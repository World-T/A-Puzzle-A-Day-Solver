import pygame
import sys
import random

# ================= 1. 全局配置与数据 =================
pygame.init()
pygame.display.set_caption("A-Puzzle-A-Day")

# 颜色定义
C_BG = (240, 235, 225)  # 整体背景色
C_BOARD = (200, 180, 150)  # 底板颜色
C_CELL = (220, 205, 180)  # 格子颜色
C_TEXT = (80, 60, 40)  # 字体颜色
C_TARGET = (220, 80, 80)  # 目标选中颜色
C_DOCK_BG = (225, 215, 200)  # 右侧工具箱的背景色

PIECE_COLORS = {
    'A': (244, 162, 97), 'B': (233, 196, 106), 'C': (42, 157, 143),
    'D': (38, 70, 83), 'E': (231, 111, 81), 'F': (138, 177, 125),
    'G': (200, 110, 150), 'H': (100, 160, 200), 'I': (180, 150, 220)
}

# 🌟 尺寸大升级
CELL_SIZE = 70  # 放到底板上 / 拖拽时的实际大尺寸
THUMB_CELL_SIZE = 28  # 放在右侧网格里的缩略图小尺寸

BOARD_COLS = 6
BOARD_ROWS = 9
WIDTH, HEIGHT = 1600, 900

BOARD_X = 500
BOARD_Y = HEIGHT // 2 - (BOARD_ROWS * CELL_SIZE) // 2

GRID_LABELS = [
    ["JAN", "FEB", "MAR", "APR", "MAY", "JUN"],
    ["JUL", "AUG", "SEP", "OCT", "NOV", "DEC"],
    ["1", "2", "3", "4", "5", "6"],
    ["7", "8", "9", "10", "11", "12"],
    ["13", "14", "15", "16", "17", "18"],
    ["19", "20", "21", "22", "23", "24"],
    ["25", "26", "27", "28", "29", "30"],
    ["31", "", "", "MON", "TUES", "WED"],
    ["", "", "THUR", "FRI", "SAT", "SUN"]
]

RAW_PIECES = {
    'A': ["A0000", "AAAAA"], 'B': ["BB00", "0BBB", "0B00"],
    'C': ["0C000", "CCCCC"], 'D': ["D0D", "DDD", "00D"],
    'E': ["E00", "EEE", "E00", "E00"], 'F': ["FFFF", "000F"],
    'G': ["0GGG", "GG00"], 'H': ["H00", "H00", "H00", "HHH"],
    'I': ["0II", "III"]
}

try:
    title_font = pygame.font.SysFont("microsoftyahei", 40, bold=True)
    font = pygame.font.SysFont("arial", 24, bold=True)
    small_font = pygame.font.SysFont("microsoftyahei", 20)
except:
    title_font = pygame.font.Font(None, 48)
    small_font = pygame.font.Font(None, 24)


# ================= 2. 核心算法类 =================
class Solver:
    def __init__(self):
        self.variants = {}
        for name, shape in RAW_PIECES.items():
            self.variants[name] = self.get_all_variants(self.parse(shape))

    def parse(self, shape_strs):
        return [(r, c) for r, row in enumerate(shape_strs) for c, char in enumerate(row) if char != '0']

    def normalize(self, coords):
        coords = sorted(coords)
        min_r, min_c = coords[0]
        return tuple((r - min_r, c - min_c) for r, c in coords)

    def get_all_variants(self, coords):
        variants = set()
        for flip in [False, True]:
            flipped = [(r, -c) if flip else (r, c) for r, c in coords]
            for _ in range(4):
                flipped = [(c, -r) for r, c in flipped]
                variants.add(self.normalize(flipped))
        return list(variants)

    def solve(self, targets):
        board = [['.' for _ in range(6)] for _ in range(9)]
        for r in range(9):
            for c in range(6):
                if (r, c) in targets:
                    board[r][c] = '*'

        piece_order = list(self.variants.keys())
        random.shuffle(piece_order)
        shuffled_variants = {k: random.sample(v, len(v)) for k, v in self.variants.items()}
        solution_placements = {}

        def dfs(used_mask):
            if used_mask == (1 << 9) - 1: return True
            empty_r, empty_c = -1, -1
            for r in range(9):
                for c in range(6):
                    if board[r][c] == '.':
                        empty_r, empty_c = r, c;
                        break
                if empty_r != -1: break
            if empty_r == -1: return False

            for i, p_name in enumerate(piece_order):
                if used_mask & (1 << i): continue
                for variant in shuffled_variants[p_name]:
                    can_place = True
                    for dr, dc in variant:
                        nr, nc = empty_r + dr, empty_c + dc
                        if nr < 0 or nr >= 9 or nc < 0 or nc >= 6 or board[nr][nc] != '.':
                            can_place = False;
                            break
                    if can_place:
                        for dr, dc in variant: board[empty_r + dr][empty_c + dc] = p_name
                        solution_placements[p_name] = (empty_r, empty_c, variant)
                        if dfs(used_mask | (1 << i)): return True
                        del solution_placements[p_name]
                        for dr, dc in variant: board[empty_r + dr][empty_c + dc] = '.'
            return False

        if dfs(0): return solution_placements
        return None


solver = Solver()


# ================= 3. 游戏 UI 组件 =================
class Piece:
    def __init__(self, name, shape_strs, color, start_x, start_y):
        self.name = name
        self.shape_strs = shape_strs  # 保存初始形状以便重置
        self.blocks = solver.normalize(solver.parse(shape_strs))
        self.color = color
        self.x, self.y = start_x, start_y
        self.start_x, self.start_y = start_x, start_y
        self.grid_pos = None
        self.is_dragging = False
        self.is_docked = True  # 🌟 新增状态：是否停留在网格中

    @property
    def current_cell_size(self):
        # 如果停留在网格中，尺寸是小的；被抓起或放下时，尺寸是大的
        return THUMB_CELL_SIZE if self.is_docked else CELL_SIZE

    def rotate(self):
        self.blocks = solver.normalize([(c, -r) for r, c in self.blocks])

    def flip(self):
        self.blocks = solver.normalize([(r, -c) for r, c in self.blocks])

    def return_to_dock(self):
        # 🌟 新增：只飞回网格，不重置形状（保留当前的旋转和翻转）
        self.is_docked = True
        self.x, self.y = self.start_x, self.start_y
        self.grid_pos = None

    def reset(self):
        # 一键恢复初始状态和缩略图尺寸
        self.blocks = solver.normalize(solver.parse(self.shape_strs))
        self.is_docked = True
        self.x, self.y = self.start_x, self.start_y
        self.grid_pos = None

    def draw(self, surface, offset_x=0, offset_y=0):
        cs = self.current_cell_size
        for r, c in self.blocks:
            px = self.x + c * cs + offset_x
            py = self.y + r * cs + offset_y
            rect = pygame.Rect(px, py, cs - 1, cs - 1)
            pygame.draw.rect(surface, self.color, rect, border_radius=4)
            pygame.draw.rect(surface, (255, 255, 255), rect, 1, border_radius=4)

    def is_hovered(self, mx, my):
        cs = self.current_cell_size
        for r, c in self.blocks:
            px = self.x + c * cs
            py = self.y + r * cs
            if px <= mx <= px + cs and py <= my <= py + cs: return True
        return False


# 🌟 生成 2x5 网格的坐标
dock_start_x = 1150
dock_start_y = 120
col_spacing = 200
row_spacing = 140

pieces = []
piece_names = list(RAW_PIECES.keys())  # A 到 I 共 9 个
for i, name in enumerate(piece_names):
    row = i // 2  # 计算在第几行 (0-4)
    col = i % 2  # 计算在第几列 (0-1)
    p_x = dock_start_x + col * col_spacing
    p_y = dock_start_y + row * row_spacing
    pieces.append(Piece(name, RAW_PIECES[name], PIECE_COLORS[name], p_x, p_y))

targets = set()
dragged_piece = None
drag_offset_x, drag_offset_y = 0, 0

# ================= 4. 主循环 =================
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()


def draw_layout():
    screen.fill(C_BG)

    # 1. 绘制右侧 2x5 工具箱背景
    pygame.draw.rect(screen, C_DOCK_BG, (1100, 70, 400, 750), border_radius=15)

    # 可选：绘制虚线的空置网格槽位暗示
    for i in range(10):
        r, c = i // 2, i % 2
        px = dock_start_x + c * col_spacing
        py = dock_start_y + r * row_spacing
        # 简单画一个圆圈作为停靠点暗示
        pygame.draw.circle(screen, (200, 190, 180), (px + THUMB_CELL_SIZE, py + THUMB_CELL_SIZE * 1.5), 40, 2)

    # 2. 绘制中间大底板
    pygame.draw.rect(screen, C_BOARD,
                     (BOARD_X - 10, BOARD_Y - 10, BOARD_COLS * CELL_SIZE + 20, BOARD_ROWS * CELL_SIZE + 20),
                     border_radius=10)
    for r in range(BOARD_ROWS):
        for c in range(BOARD_COLS):
            lbl = GRID_LABELS[r][c]
            rect = pygame.Rect(BOARD_X + c * CELL_SIZE, BOARD_Y + r * CELL_SIZE, CELL_SIZE - 2, CELL_SIZE - 2)
            bg_color = C_TARGET if (r, c) in targets else C_CELL
            pygame.draw.rect(screen, bg_color, rect, border_radius=6)
            if lbl:
                txt = font.render(lbl, True, C_TEXT if (r, c) not in targets else (255, 255, 255))
                screen.blit(txt, txt.get_rect(center=rect.center))

    # 3. 绘制左侧文字说明
    title = title_font.render("A-Puzzle-A-Day", True, C_TEXT)
    screen.blit(title, (60, 100))

    instructions = [
        "【操作说明】",
        "1. 设定日期：",
        "   点击底板选取 月、日、星期",
        "",
        "2. 手动挑战：",
        "   鼠标拖拽右侧缩略图放入底板",
        "   抓起时自动放大",
        "   悬停时按 [R] 旋转，按 [F] 翻转",
        "",
        "3. 电脑代打：",
        "   按 [空格键] 瞬间自动求解！",
        "   再次按下切换不同解法。",
        "",
        "4. 重置：",
        "   按 [C] 键清空并重置网格",
        "",
        "  提示：确保关闭中文输入法"
    ]
    y_offset = 180
    for line in instructions:
        color = (200, 80, 80) if "提示" in line else (100, 100, 100)
        try:
            txt = small_font.render(line, True, color)
            screen.blit(txt, (60, y_offset))
        except:
            pass
        y_offset += 35


running = True
while running:
    mx, my = pygame.mouse.get_pos()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                clicked_piece = False
                for p in reversed(pieces):
                    if p.is_hovered(mx, my):
                        # 🌟 关键交互：抓起瞬间变大，需要保持鼠标在同一方块上
                        old_cs = p.current_cell_size
                        # 找出鼠标正停留在拼图的哪一个小方块上
                        clicked_r, clicked_c = 0, 0
                        for br, bc in p.blocks:
                            px = p.x + bc * old_cs
                            py = p.y + br * old_cs
                            if px <= mx <= px + old_cs and py <= my <= py + old_cs:
                                clicked_r, clicked_c = br, bc
                                break

                        dragged_piece = p
                        p.is_dragging = True
                        p.is_docked = False  # 状态变为不驻留网格 -> 触发大尺寸绘制

                        # 重新计算坐标：让放大后的大方块的中心点，对齐现在的鼠标位置
                        new_cs = CELL_SIZE
                        p.x = mx - clicked_c * new_cs - new_cs // 2
                        p.y = my - clicked_r * new_cs - new_cs // 2

                        drag_offset_x = p.x - mx
                        drag_offset_y = p.y - my

                        pieces.remove(p)
                        pieces.append(p)
                        p.grid_pos = None
                        clicked_piece = True
                        break

                if not clicked_piece:
                    c = (mx - BOARD_X) // CELL_SIZE
                    r = (my - BOARD_Y) // CELL_SIZE
                    if 0 <= r < BOARD_ROWS and 0 <= c < BOARD_COLS and GRID_LABELS[r][c] != "":
                        if (r, c) in targets:
                            targets.remove((r, c))
                        elif len(targets) < 3:
                            targets.add((r, c))

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1 and dragged_piece:
                nearest_c = round((dragged_piece.x - BOARD_X) / CELL_SIZE)
                nearest_r = round((dragged_piece.y - BOARD_Y) / CELL_SIZE)

                valid_placement = True
                for br, bc in dragged_piece.blocks:
                    gr, gc = nearest_r + br, nearest_c + bc
                    if gr < 0 or gr >= BOARD_ROWS or gc < 0 or gc >= BOARD_COLS:
                        valid_placement = False;
                        break

                if valid_placement:
                    dragged_piece.x = BOARD_X + nearest_c * CELL_SIZE
                    dragged_piece.y = BOARD_Y + nearest_r * CELL_SIZE
                    dragged_piece.grid_pos = (nearest_r, nearest_c)
                else:
                    # 如果没放到底板上，调用 reset 瞬间缩小并飞回原处
                    dragged_piece.return_to_dock()

                dragged_piece.is_dragging = False
                dragged_piece = None

        elif event.type == pygame.MOUSEMOTION:
            if dragged_piece:
                dragged_piece.x = mx + drag_offset_x
                dragged_piece.y = my + drag_offset_y

        elif event.type == pygame.KEYDOWN:
            target_piece = dragged_piece
            if not target_piece:
                for p in reversed(pieces):
                    if p.is_hovered(mx, my):
                        target_piece = p
                        break
            if target_piece:
                # 只有从网格抓出来了(非docked状态)才允许翻转，逻辑更严谨
                if not target_piece.is_docked:
                    if event.key == pygame.K_r:
                        target_piece.rotate()
                    elif event.key == pygame.K_f:
                        target_piece.flip()

            if event.key == pygame.K_c:
                for p in pieces: p.reset()
                targets.clear()

            if event.key == pygame.K_SPACE:
                if len(targets) != 3:
                    print("请先在底板上点击选中 3 个要空出来的格子！")
                else:
                    for p in pieces: p.reset()
                    draw_layout()
                    for p in pieces: p.draw(screen)
                    pygame.display.flip()

                    solution = solver.solve(targets)
                    if solution:
                        for p in pieces:
                            if p.name in solution:
                                r, c, final_blocks = solution[p.name]
                                p.blocks = final_blocks
                                p.grid_pos = (r, c)
                                p.is_docked = False  # 设置为放大状态
                                p.x = BOARD_X + c * CELL_SIZE
                                p.y = BOARD_Y + r * CELL_SIZE
                    else:
                        print("抱歉，此组合无解！")

    draw_layout()

    for p in pieces:
        if not p.is_dragging: p.draw(screen)
    if dragged_piece:
        dragged_piece.draw(screen, offset_x=5, offset_y=5)

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()