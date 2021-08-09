import pygame
import pygame.font
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import nearest_points
from Network import Network
import pickle
import itertools

DOT_RADIUS = 8
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 900

pygame.init()
pygame.font.init()
clock = pygame.time.Clock()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))

dragging = False
p1_turn = True
turn_font = pygame.font.SysFont("arial", 30)
turn_text = None
dot_list = []
line_list = []
cur_line = []
overlap = False
dot_mode = False
cur_display_dot = None
found_loop = False
loop_line_list = []
last_line_in_loop = None
poly_list = []
n = None

class Dot():
    def __init__(self, da_point, num_con):
        self.xval = da_point.x
        self.yval = da_point.y
        self.point = da_point
        self.num_con = num_con
        self.marked = False
        self.in_or_on_poly = []
        self.on_poly = []

    def draw_self(self):
        pygame.draw.circle(screen, "black", (self.xval, self.yval), DOT_RADIUS)

class Line():
    def __init__(self, point_list, start, end):
        self.line_string = LineString(point_list)
        self.point_list = point_list
        self.start = start
        self.end = end
        self.marked = False
        self.prev_line = None
        self.adj_lines = []

    def find_adj(self):
        self.adj_lines.clear()
        for line in line_list:
            if (line.start == self.start or line.start == self.end or line.end == self.start or line.end == self.end) and line != self:
                self.adj_lines.append(line)

    def reverse(self):
        temp = self.start
        self.start = self.end
        self.end = temp
        self.point_list.reverse()
        self.line_string = LineString(self.point_list)

def remove_consecutive_dups(list):
    return [i[0] for i in itertools.groupby(list)]

def remove_start_and_end_overlap(line, start_dot, end_dot):
    finished_line = line.copy()
    for point in line:
        if (abs(point[0] - start_dot.xval) <= DOT_RADIUS - 2) and ((abs(point[1] - start_dot.yval) <= DOT_RADIUS - 2)):
            finished_line.remove(point)
        else:
            break
    for point2 in reversed(line):
        if (abs(point2[0] - end_dot.xval) <= DOT_RADIUS - 2) and ((abs(point2[1] - end_dot.yval) <= DOT_RADIUS - 2)):
            finished_line.remove(point2)
        else:
            break
    return finished_line

def update_dot_boundings():
    for dot in dot_list:
        dot.on_poly.clear()
        dot.in_or_on_poly.clear()
        for poly in poly_list:
            if poly.contains(dot.point) or poly.touches(dot.point):
                dot.in_or_on_poly.append(poly)
            if poly.touches(dot.point):
                dot.on_poly.append(poly)

def available_moves():
    for dot in dot_list:
        if dot.num_con < 2:
            return True
        if dot.num_con == 3:
            continue
        for con_dot in dot_list:
            if dot == con_dot:
                continue
            if con_dot.num_con == 3:
                continue
            for poly in dot.in_or_on_poly:
                if poly in con_dot.in_or_on_poly:
                    return True
            if len(dot.in_or_on_poly) == 0 and len(con_dot.in_or_on_poly) == 0:
                return True
            if (len(dot.on_poly) < 2 and (dot.in_or_on_poly == dot.on_poly)) and (len(con_dot.on_poly) < 2 and (con_dot.in_or_on_poly == con_dot.on_poly)):
                return True
    return False

def update_misc(available_bool):
    global turn_text
    if p1_turn and not available_bool:
        turn_text = turn_font.render("Player 2 Wins!", True, (0,0,0))
    elif not p1_turn and not available_bool:
        turn_text = turn_font.render("Player 1 Wins!", True, (0,0,0))
    elif p1_turn:
        turn_text = turn_font.render("Player 1's Turn", True, (0,0,0))
    else:
        turn_text = turn_font.render("Player 2's Turn", True, (0,0,0))

def fix_loop_list(loop_line_list):
    to_return = []
    front_con = False
    back_con = False
    for x in loop_line_list:
        for y in loop_line_list:
            if (x != y and y.line_string.intersects(Point(x.point_list[0]))):
                front_con = True
            if (x != y and y.line_string.intersects(Point(x.point_list[-1]))):
                back_con = True
        if not (front_con and back_con):
            x.marked = True
        front_con = False
        back_con = False
    for line in loop_line_list:
        if not line.marked:
            to_return.append(line)
    for line in loop_line_list:
        line.marked = False
    return to_return

def area_func(poly):
    return poly.area

def add_to_poly_list(loop_poly):
    global poly_list
    new_poly_list = []
    engulfing_poly = None
    poly_list.sort(reverse = True, key = area_func)
    cur_section = loop_poly
    for poly in poly_list:
        if cur_section.contains(poly):
            cur_section = cur_section.difference(poly)
    for poly in poly_list:
        if poly.contains(cur_section):
            engulfing_poly = poly
            fixed_section = poly.difference(cur_section)
    for poly in poly_list:
        if poly == engulfing_poly:
            new_poly_list.append(fixed_section)
        else:
            new_poly_list.append(poly)
    new_poly_list.append(cur_section)
    poly_list = new_poly_list

def split_line_at_dot(line, dot):
    intersect_point = Point(dot.xval, dot.yval)
    for x in range(0, len(line) -1):
        cur_line_segment = LineString([line[x], line[x+1]])
        if cur_line_segment.distance(intersect_point) < .1:
            split_index = x
            break
    ret_line = []
    temp_line = line[:split_index]
    temp_line.append((dot.xval, dot.yval))
    ret_line.append(temp_line)
    temp_line_2 = line[split_index + 1:]
    temp_line_2.insert(0,(dot.xval, dot.yval))
    ret_line.append(temp_line_2)
    return ret_line

def check_loop(cur_line, end_point):
    global found_loop
    global last_line_in_loop
    if found_loop:
        return
    cur_line.marked = True
    if cur_line.end == end_point or cur_line.start == end_point:
        last_line_in_loop = cur_line
        found_loop = True
        return
    cur_line.find_adj()
    for line in cur_line.adj_lines:
        if not line.marked:
            line.prev_line = cur_line
            check_loop(line, end_point)

def sort_loop(loop):
    cur_line = loop[-1]
    start_dot = cur_line.start
    to_return = []
    to_return.append(cur_line)
    while (cur_line.end != start_dot) or (cur_line == loop[0]):
        for line in loop:
            if cur_line != line and cur_line.end == line.start:
                to_return.append(line)
                cur_line = line
                break
            if cur_line != line and cur_line.end == line.end:
                line.reverse()
                to_return.append(line)
                cur_line = line
                break
    return to_return

def draw_lines():
    for line in line_list:
        pygame.draw.lines(screen, "black", False, line.point_list, width = 4)

def draw_cur_line():
    if(len(cur_line) > 1 ):
       pygame.draw.lines(screen, "black", False, cur_line, width = 4)

def draw_intro():
    if n.id == 0:
        intro_text = turn_font.render("Click to place starting dots. Press enter to start!", True, (0,0,0))
    else:
        intro_text = turn_font.render("Waiting for player 1 to place starting dots...", True, (0,0,0))
    screen.blit(intro_text, ((SCREEN_WIDTH / 2) - (intro_text.get_rect().width / 2), 20))

def draw_dots():
    for dot in dot_list:
        dot.draw_self()

def draw_cur_dot():
    if cur_display_dot:
        pygame.draw.circle(screen, "red", (cur_display_dot.x, cur_display_dot.y), DOT_RADIUS)

def draw_misc():
    global turn_text
    if turn_text == None:
        default_text = turn_font.render("Player 1's Turn", True, (0,0,0))
        screen.blit(default_text,((SCREEN_WIDTH / 2) - (default_text.get_rect().width / 2), 20))
    else:
        screen.blit(turn_text,((SCREEN_WIDTH / 2) - (turn_text.get_rect().width / 2), 20))

# initialize dot_list with none so checking last element is always valid
def setup_server_sync(received_data):
    global cur_display_dot
    if len(dot_list) == 0:
        if received_data[0] != None:
            new_dot = Dot(received_data[0], 0)
            dot_list.append(new_dot)
    elif received_data[0] != dot_list[-1].point:
        new_dot = Dot(received_data[0], 0)
        dot_list.append(new_dot)
    if received_data[1] != cur_display_dot and received_data[1] != None:
        cur_display_dot = received_data[1]


def set_up_board():
    global n
    global cur_display_dot
    while True:
        screen.fill((230, 230, 230))
        draw_cur_dot()
        draw_dots()
        draw_intro()
        clock.tick(60)
        pygame.display.flip()
        if n.id == 0:
            if len(dot_list) == 0:
                to_send_list = [None, cur_display_dot]
            else:
                to_send_list = [dot_list[-1].point, cur_display_dot]
            n.send(to_send_list)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    raise SystemExit
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and cur_display_dot:
                    new_dot = Dot(cur_display_dot, 0)
                    dot_list.append(new_dot)
                    pass
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                    cur_display_dot = None
                    return
            mpos = pygame.mouse.get_pos()
            mpos_point = Point(mpos)
            cur_display_dot = mpos_point
            for dot in dot_list:
                if dot.point.distance(mpos_point) < DOT_RADIUS * 4:
                    cur_display_dot = None
                    break
        else:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    raise SystemExit
            received_list = n.send([True, 4])
            setup_server_sync(received_list)

pygame.display.set_caption("Sprouts")
n = Network()
print(n.id)
set_up_board()

while True:
    screen.fill((230, 230, 230))
    draw_dots()
    draw_cur_line()
    draw_lines()
    draw_cur_dot()
    draw_misc()
    clock.tick(60)
    pygame.display.flip()
    if not n.id == p1_turn:
        cur_line = remove_consecutive_dups(cur_line)
        to_send_list = [p1_turn, dot_list[-1].point, cur_display_dot, cur_line]
        n.send(to_send_list)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise SystemExit
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mpos = pygame.mouse.get_pos()
                if not dot_mode:
                    for dot in dot_list:
                        if (abs(mpos[0] - dot.xval) <= DOT_RADIUS - 2) and (abs(mpos[1] - dot.yval) <= DOT_RADIUS - 2):
                            start_dot = dot
                            dragging = True
                elif cur_display_dot:
                    new_dot = Dot(cur_display_dot, 2)
                    dot_list.append(new_dot)
                    # put inside function
                    two_lines = split_line_at_dot(line_list[-1].point_list, new_dot)
                    line1 = Line(two_lines[0], start_dot, new_dot)
                    line2 = Line(two_lines[1], new_dot, end_dot)
                    line_list[-1] = line1
                    line_list[-1].marked = True
                    line_list.append(line2)
                    line_list[-1].find_adj()
                    if len(line_list[-1].adj_lines) > 1:
                        check_loop(line_list[-1], start_dot)
                    for line in line_list:
                        line.marked = False
                    if found_loop:
                        loop_line_list.clear()
                        if start_dot == end_dot:
                            loop_line_list.append(line1)
                            loop_line_list.append(line2)
                            loop_poly = Polygon(line1.point_list + line2.point_list) 
                        else:
                            temp_line = last_line_in_loop
                            big_line = []
                            while temp_line.prev_line != None:
                                loop_line_list.append(temp_line)
                                temp_line = temp_line.prev_line
                            loop_line_list.append(line1)
                            loop_line_list.append(line2)
                            loop_line_list = fix_loop_list(loop_line_list)
                            pre_line = None
                            sorted_loop = sort_loop(loop_line_list)
                            for line in sorted_loop:
                                big_line += line.point_list
                            loop_poly = Polygon(big_line)
                        add_to_poly_list(loop_poly)
                    found_loop = False
                    cur_display_dot = None
                    dot_mode = False
                    update_dot_boundings()
                    available_bool = available_moves()
                    p1_turn = not p1_turn
                    update_misc(available_bool)
            elif event.type == pygame.MOUSEBUTTONUP:
                overlap = False
                if event.button == 1 and dragging:
                    dragging = False
                    for dot in dot_list:
                        if (abs(mpos[0] - dot.xval) <= DOT_RADIUS - 2) and (abs(mpos[1] - dot.yval) <= DOT_RADIUS - 2):
                            no_dups = remove_start_and_end_overlap(remove_consecutive_dups(cur_line), start_dot, dot)
                            temp_line_string = LineString(no_dups)
                            no_dups.append((dot.xval, dot.yval))
                            no_dups.insert(0,(start_dot.xval, start_dot.yval))
                            real_line_string = LineString(no_dups)
                            for line in line_list:
                                if temp_line_string.intersects(line.line_string):
                                    overlap = True
                                    break
                            for other_dot in dot_list:
                                if other_dot != dot and other_dot != start_dot:
                                    for point in no_dups:
                                        if (abs(point[0] - other_dot.xval) <= DOT_RADIUS - 1 ) and ((abs(point[1] - other_dot.yval) <= DOT_RADIUS - 1)):
                                            overlap = True
                            if start_dot is dot and not overlap and real_line_string.is_simple:
                                end_dot = dot
                                if start_dot.num_con < 2:
                                    start_dot.num_con += 2
                                    new_line = Line(no_dups, start_dot, end_dot)
                                    line_list.append(new_line)
                                    found_loop = True
                                    dot_mode = True
                                break
                            elif dot.num_con < 3 and start_dot.num_con < 3 and not overlap and real_line_string.is_simple:
                                end_dot = dot
                                dot.num_con += 1
                                start_dot.num_con += 1
                                new_line = Line(no_dups, start_dot, end_dot)
                                line_list.append(new_line)
                                dot_mode = True
                                break
                cur_line.clear()
            mpos2 = pygame.mouse.get_pos()
            mpos2_point = Point(mpos2) 
        if dragging:
            cur_line.append(mpos)
            mpos = mpos2
        elif dot_mode:
            if mpos2_point.distance(Point(start_dot.xval, start_dot.yval)) > DOT_RADIUS + 9 and mpos2_point.distance(Point(end_dot.xval, end_dot.yval)) > DOT_RADIUS + 9:
                if line_list[-1].line_string.distance(mpos2_point) < 10:
                    cur_display_dot = nearest_points(line_list[-1].line_string, Point(mpos2[0],mpos2[1]))[0]
                else:
                    cur_display_dot = None
            else:
                cur_display_dot = None
    else:
        pass