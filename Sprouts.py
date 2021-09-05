import pygame
import pygame.font
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import nearest_points
from Network import Network
from base64 import b64encode, b64decode
import threading
import Server
import socket
import itertools
import urllib.request


DOT_RADIUS = 8
SCREEN_WIDTH = 1300
SCREEN_HEIGHT = 975

pygame.init()
pygame.font.init()
clock = pygame.time.Clock()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.scrap.init()

# Ugly global variables, will clean up later 
dragging = False
p1_turn = True
available_bool = True
wins = [0,0]
turn_font = pygame.font.SysFont("arial", 30)
smaller_font = pygame.font.SysFont("arial", 28)
win_font = pygame.font.SysFont("arial", 20)
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

    def find_start_end(self):
        for dot in dot_list:
            if dot.point == Point(self.point_list[0]):
                self.start = dot
            if dot.point == Point(self.point_list[-1]):
                self.end = dot

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
    if len(finished_line) < 1:
        return []
    for point2 in reversed(line):
        if (abs(point2[0] - end_dot.xval) <= DOT_RADIUS - 2) and ((abs(point2[1] - end_dot.yval) <= DOT_RADIUS - 2)):
            finished_line.remove(point2)
        else:
            break
    return finished_line

def remove_dot_dups():
    global dot_list
    new_dot_list = []
    for dot in dot_list:
        if dot not in new_dot_list:
            new_dot_list.append(dot)
    dot_list = new_dot_list

def remove_line_dups():
    global line_list
    new_line_list = []
    is_dup = False
    for line in line_list:
        for new_line in new_line_list:
            if line.point_list == new_line.point_list:
                is_dup = True
        if not is_dup:
            new_line_list.append(line)
        is_dup = False
    line_list = new_line_list           

def update_dot_boundings():
    for dot in dot_list:
        dot.on_poly.clear()
        dot.in_or_on_poly.clear()
        for poly in poly_list:
            if poly.contains(dot.point) or poly.touches(dot.point):
                dot.in_or_on_poly.append(poly)
            if poly.touches(dot.point):
                dot.on_poly.append(poly)

def update_misc():
    global available_bool
    global turn_text
    global wins
    global p1_turn
    winner = 0
    if available_bool:
        if p1_turn:
            turn_text = turn_font.render("Player 1's Turn", True, (0,0,0))
        else:
            turn_text = turn_font.render("Player 2's Turn", True, (0,0,0))
    else:
        if p1_turn:
            winner = 1
            wins[1] += 1
        else:
            wins[0] += 1
        if winner == n.id:
            turn_text = turn_font.render("You Win!", True, (0,0,0))
        else:
            turn_text = turn_font.render("You Lose!", True, (0,0,0))

def available_moves():
    global available_bool
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
                available_bool = True
                return
            if (len(dot.on_poly) < 2 and (dot.in_or_on_poly == dot.on_poly)) and (len(con_dot.on_poly) < 2 and (con_dot.in_or_on_poly == con_dot.on_poly)):
                available_bool = True
                return
    available_bool = False
    return

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

def draw_game_setup(phase_tracker):
    waiting_text = None
    if phase_tracker == 0:
        setup_text = turn_font.render("Press Enter to start hosting a game, or press Space to connect to a host.", True, (0,0,0))
    elif phase_tracker == 1:
        setup_text = smaller_font.render("Connection code has been copied to clipboard. Send this code to your friend to start playing!", True, (0,0,0))
        waiting_text = turn_font.render("Waiting for Player 2 to connect...", True, (0,0,0))
    elif phase_tracker == 2:
        setup_text = turn_font.render("Copy the host's connection code to your clipboard, then press Enter to play!", True, (0,0,0))
    elif phase_tracker == 3:
        setup_text = smaller_font.render("Invalid connection code. Please copy the host's connection code and try again!", True, (0,0,0))
    screen.blit(setup_text, ((SCREEN_WIDTH / 2) - (setup_text.get_rect().width / 2), 20))
    if waiting_text:
        screen.blit(waiting_text, ((SCREEN_WIDTH / 2) - (waiting_text.get_rect().width / 2), (SCREEN_HEIGHT / 2) - (waiting_text.get_rect().height / 2)))

def draw_lines():
    for line in line_list:
        pygame.draw.lines(screen, "black", False, line.point_list, width = 4)

def draw_cur_line():
    if(len(cur_line) > 1 ):
       pygame.draw.lines(screen, "black", False, cur_line, width = 4)

def draw_dots():
    for dot in dot_list:
        dot.draw_self()

def draw_cur_dot():
    if cur_display_dot:
        pygame.draw.circle(screen, "red", (cur_display_dot.x, cur_display_dot.y), DOT_RADIUS)

def draw_intro():
    if n.id == 0:
        intro_text = turn_font.render("Click to place starting dots. Press enter to start!", True, (0,0,0))
    else:
        intro_text = turn_font.render("Waiting for player 1 to place starting dots...", True, (0,0,0))
    screen.blit(intro_text, ((SCREEN_WIDTH / 2) - (intro_text.get_rect().width / 2), 20))

def draw_wins():
    global wins
    global win_font
    p1_wins = win_font.render("Player 1 Wins: " + str(wins[0]), True, (40,40,220))
    p2_wins = win_font.render("Player 2 Wins: " + str(wins[1]), True, (220,40,40))
    screen.blit(p1_wins, (20, 30))
    screen.blit(p2_wins, (SCREEN_WIDTH - 20 - p2_wins.get_rect().width, 30))

def draw_misc():
    global turn_font
    global turn_text
    global n 
    global available_bool
    if turn_text == None:
        default_text = turn_font.render("Player 1's Turn", True, (0,0,0))
        screen.blit(default_text,((SCREEN_WIDTH / 2) - (default_text.get_rect().width / 2), 20))
    else:
        screen.blit(turn_text,((SCREEN_WIDTH / 2) - (turn_text.get_rect().width / 2), 20))
    if not available_bool:
        if n.id == 0:
            replay_text = turn_font.render("Press Enter to play again!", True, (0,0,0))
        else:
            replay_text = turn_font.render("Waiting for Player 1 to restart game...", True, (0,0,0))
        screen.blit(replay_text, ((SCREEN_WIDTH / 2) - (replay_text.get_rect().width / 2), 80))

def setup_server_sync(received_data):
    global cur_display_dot
    if received_data == None or received_data == 0:
        pygame.quit()
        raise SystemExit
    if received_data == 99:
        return
    if len(dot_list) == 0:
        if received_data[0] != None:
            new_dot = Dot(received_data[0], 0)
            dot_list.append(new_dot)
    elif received_data[0] != dot_list[-1].point:
        new_dot = Dot(received_data[0], 0)
        dot_list.append(new_dot)
    if received_data[1] != cur_display_dot and received_data[1] != None:
        cur_display_dot = received_data[1]

def main_server_sync(received_data):
    global cur_display_dot
    global cur_line
    global line_list
    global found_loop
    if received_data == None or received_data == 0:
        pygame.quit()
        raise SystemExit
    if received_data == 99 or (type(received_data) is list and len(received_data) < 3):
        return
    if received_data[1] != cur_display_dot:
        cur_display_dot = received_data[1]
    if received_data[2] != cur_line:
        cur_line = received_data[2]
    if len(line_list) == 0:
        if received_data[3] != None and len(received_data[3]) > 1:
            new_line = Line(received_data[3], None, None)
            new_line.find_start_end()
            new_line.start.num_con += 1
            new_line.end.num_con += 1
            line_list.append(new_line)
    elif line_list[-1].point_list != received_data[3] and received_data[0] == dot_list[-1].point:
            new_line = Line(received_data[3], None, None)
            new_line.find_start_end()
            new_line.start.num_con += 1
            new_line.end.num_con += 1
            line_list.append(new_line)
    if received_data[0] != dot_list[-1].point:
        new_dot = Dot(received_data[0], 2)
        dot_list.append(new_dot)
        line1 = Line(received_data[3], None, None)
        line1.find_start_end()
        line2 = Line(received_data[4], None, None)
        line2.find_start_end()
        line_list[-1] = line2
        line_list.append(line1)
        line_list[-1].find_adj()
        if line2.start == line1.end:
            found_loop = True
        update_backend(line2, line1)

def set_up_game():
    global n
    phase_tracker = 0
    while True:
        screen.fill((230, 230, 230))
        draw_game_setup(phase_tracker)
        clock.tick(60)
        pygame.display.flip()
        if phase_tracker == 1:
            p2_connected = n.send(4)
            if p2_connected:
                return
        if phase_tracker >= 2:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    raise SystemExit
                if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                    reversed = pygame.scrap.get("text/plain;charset=utf-8").decode()
                    b64_ip = reversed[::-1]
                    b_b64_ip = b64_ip.encode("ascii")
                    try:
                        b_external_ip = b64decode(b_b64_ip)
                        external_ip = b_external_ip.decode("ascii")
                    except:
                        external_ip = "BAD CODE"
                    n = Network(external_ip)
                    if n.id == -1:
                        phase_tracker = 3
                    else:
                        return
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN and phase_tracker == 0:
                external_ip = urllib.request.urlopen('https://v4.ident.me/').read().decode('utf8')
                b_external_ip = external_ip.encode("ascii")
                b_b64_ip = b64encode(b_external_ip)
                b64_ip = b_b64_ip.decode("ascii")
                to_send = b64_ip[::-1]
                pygame.scrap.put("text/plain;charset=utf-8", to_send.encode("utf-8"))
                thread = threading.Thread(target=Server.start_server, args = ())
                thread.daemon = True
                thread.start()
                phase_tracker = 1
                local_ip = socket.gethostbyname(socket.gethostname())
                n = Network(local_ip)   
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE and phase_tracker == 0:
                phase_tracker = 2
            
def set_up_board():
    global n
    global cur_display_dot
    while True:
        screen.fill((230, 230, 230))
        draw_cur_dot()
        draw_dots()
        draw_intro()
        draw_wins()
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
                    n.send(22)
                    pygame.quit()
                    raise SystemExit
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and cur_display_dot:
                    new_dot = Dot(cur_display_dot, 0)
                    dot_list.append(new_dot)
                    pass
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                    cur_display_dot = None
                    n.send(24)
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
                    pygame.quit()
                    raise SystemExit
            received_list = n.send([True, 4])
            if (received_list == 48):
                break
            setup_server_sync(received_list)


def update_backend(line1, line2):
    global found_loop
    global loop_line_list
    global p1_turn
    global cur_display_dot
    global dot_mode

    start_dot = line1.start
    end_dot = line2.end
    remove_line_dups()
    remove_dot_dups()
    line_list[-2].marked = True
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
            sorted_loop = sort_loop(loop_line_list)
            for line in sorted_loop:
                big_line += line.point_list
            loop_poly = Polygon(big_line)
        add_to_poly_list(loop_poly)
    found_loop = False
    cur_display_dot = None
    dot_mode = False
    update_dot_boundings()
    available_moves()
    n.send([dot_list[-1].point, cur_display_dot, cur_line, line_list[-1].point_list, line_list[-2].point_list])
    n.send(12)
    p1_turn = not p1_turn
    update_misc() 

pygame.display.set_caption("Sprouts")
set_up_game()
set_up_board()

# TODO: break main loop into more readable functions, encrypt ip
while True:
    screen.fill((230, 230, 230))
    draw_dots()
    draw_cur_line()
    draw_lines()
    draw_cur_dot()
    draw_misc()
    draw_wins()
    clock.tick(60)
    pygame.display.flip()
    if n.id == 0 and not available_bool:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                n.send(22)
                pygame.quit()
                raise SystemExit
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                n.send(33)
                dot_list.clear()
                line_list.clear()
                poly_list.clear()
                loop_line_list.clear()
                available_bool = True
                set_up_board()
                p1_turn = True
                update_misc()
    if not n.id == p1_turn and available_bool:
        cur_line = remove_consecutive_dups(cur_line)
        if len(line_list) < 1:
            to_send_list = [dot_list[-1].point, cur_display_dot, cur_line, None, None]
        else:
            to_send_list = [dot_list[-1].point, cur_display_dot, cur_line, line_list[-1].point_list, None]
        n.send(to_send_list)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                n.send(22)
                pygame.quit()
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
                    line_list.append(line2)
                    line_list[-1].find_adj()
                    update_backend(line1, line2)
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                overlap = False
                if event.button == 1 and dragging:
                    dragging = False
                    for dot in dot_list:
                        if (abs(mpos[0] - dot.xval) <= DOT_RADIUS - 2) and (abs(mpos[1] - dot.yval) <= DOT_RADIUS - 2):
                            no_dups = remove_start_and_end_overlap(remove_consecutive_dups(cur_line), start_dot, dot)
                            if len(no_dups) < 1:
                                break
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
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit
        if n.id == 0 and not available_bool:
            continue
        received_list = n.send([True, 4])
        if received_list == 33 and n.id == 1:
            dot_list.clear()
            line_list.clear()
            poly_list.clear()
            loop_line_list.clear()
            available_bool = True
            set_up_board()
            p1_turn = True
            update_misc()
        else:
            main_server_sync(received_list)
            