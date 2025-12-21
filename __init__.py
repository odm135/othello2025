from sakura import othello

# ====== 設定 ======
INF = 10**9
SIZE = 6

MAX_DEPTH = 6
ENDGAME_EMPTY = 8
MOB_W = 8
FRONT_W = 18

# 置換表（Transposition Table）
EXACT, LOWER, UPPER = 0, 1, 2
TT = {}

# 重み（位置評価）
WEIGHTS = [
    [100, -20, 10, 10, -20, 100],
    [-20, -50, -2, -2, -50, -20],
    [10,  -2,  5,  5,  -2, 10],
    [10,  -2,  5,  5,  -2, 10],
    [-20, -50, -2, -2, -50, -20],
    [100, -20, 10, 10, -20, 100],
]

# 角・危険マス
CORNERS = {(0, 0), (0, 5), (5, 0), (5, 5)}
X_SQUARES = {(1, 1), (1, 4), (4, 1), (4, 4)}
C_SQUARES = {(0, 1), (1, 0), (0, 4), (4, 0), (5, 1), (1, 5), (5, 4), (4, 5)}

DIR8 = [(-1, -1), (0, -1), (1, -1),
        (-1,  0),          (1,  0),
        (-1,  1), (0,  1), (1,  1)]


# ====== 基本処理 ======
def inb(x, y):
    return 0 <= x < SIZE and 0 <= y < SIZE


def get_legal_place(board, color):
    legal = []
    for y in range(SIZE):
        for x in range(SIZE):
            if othello.can_place_x_y(board, color, x, y):
                legal.append((x, y))
    return legal


def move(board, color, x, y):
    nb = othello.copy(board)
    othello.move_stone(nb, color, x, y)
    return nb


def count_empty(board):
    return sum(r.count(0) for r in board)


def game_end(board):
    return (not get_legal_place(board, 1)) and (not get_legal_place(board, 2))


# ====== 評価関数（強化版） ======
def evaluate_pos(board, my_color):
    opp = 3 - my_color
    my_score = 0
    opp_score = 0
    for y in range(SIZE):
        for x in range(SIZE):
            v = board[y][x]
            w = WEIGHTS[y][x]
            if v == my_color:
                my_score += w
            elif v == opp:
                opp_score += w
    return my_score - opp_score


def evaluate_final(board, my_color):
    opp = 3 - my_color
    my_stones = sum(r.count(my_color) for r in board)
    opp_stones = sum(r.count(opp) for r in board)
    return (my_stones - opp_stones) * 1000


def frontier_count(board, color):
    cnt = 0
    for y in range(SIZE):
        for x in range(SIZE):
            if board[y][x] != color:
                continue
            for dx, dy in DIR8:
                nx, ny = x + dx, y + dy
                if inb(nx, ny) and board[ny][nx] == 0:
                    cnt += 1
                    break
    return cnt


def corner_related_score(board, my_color):
    opp = 3 - my_color
    s = 0

    CORNER_BONUS = 800
    for (x, y) in CORNERS:
        if board[y][x] == my_color:
            s += CORNER_BONUS
        elif board[y][x] == opp:
            s -= CORNER_BONUS

    X_PENALTY = 260
    C_PENALTY = 130

    corner_map = {
        (0, 0): {"x": (1, 1), "cs": [(0, 1), (1, 0)]},
        (0, 5): {"x": (1, 4), "cs": [(0, 4), (1, 5)]},
        (5, 0): {"x": (4, 1), "cs": [(4, 0), (5, 1)]},
        (5, 5): {"x": (4, 4), "cs": [(4, 5), (5, 4)]},
    }

    for (cx, cy), info in corner_map.items():
        corner_v = board[cy][cx]
        x_sq = info["x"]
        c_sqs = info["cs"]

        if corner_v == my_color:
            if board[x_sq[1]][x_sq[0]] == my_color:
                s += 30
            for (sx, sy) in c_sqs:
                if board[sy][sx] == my_color:
                    s += 20
            continue

        if corner_v == opp:
            if board[x_sq[1]][x_sq[0]] == my_color:
                s -= X_PENALTY
            elif board[x_sq[1]][x_sq[0]] == opp:
                s += X_PENALTY

            for (sx, sy) in c_sqs:
                if board[sy][sx] == my_color:
                    s -= C_PENALTY
                elif board[sy][sx] == opp:
                    s += C_PENALTY
            continue

        # corner empty
        if board[x_sq[1]][x_sq[0]] == my_color:
            s -= X_PENALTY
        elif board[x_sq[1]][x_sq[0]] == opp:
            s += X_PENALTY

        for (sx, sy) in c_sqs:
            if board[sy][sx] == my_color:
                s -= C_PENALTY
            elif board[sy][sx] == opp:
                s += C_PENALTY

    return s


def parity_score(board):
    # 終盤だけ、弱めに効かせる（読み切り前の補助）
    empties = count_empty(board)
    if empties > 10:
        return 0
    return 15 if (empties % 2 == 1) else -15


def evaluate(board, my_color):
    """中盤評価：位置 + mobility + frontier + 角周り + (弱)parity"""
    opp = 3 - my_color

    base = evaluate_pos(board, my_color)

    my_moves = len(get_legal_place(board, my_color))
    opp_moves = len(get_legal_place(board, opp))
    mob = my_moves - opp_moves

    my_front = frontier_count(board, my_color)
    opp_front = frontier_count(board, opp)
    front = my_front - opp_front  # 自分が多いほど不利

    corner_s = corner_related_score(board, my_color)
    par = parity_score(board)

    return base + corner_s + par + MOB_W * mob - FRONT_W * front


# ====== 置換表（TT） ======
def board_key(board, turn):
    # 手番込み（同盤面でも手番で価値が変わる）
    return (turn, tuple(tuple(r) for r in board))


def tt_probe(key, depth, alpha, beta):
    e = TT.get(key)
    if e is None:
        return None, alpha, beta
    d, v, flag = e
    if d < depth:
        return None, alpha, beta
    if flag == EXACT:
        return v, alpha, beta
    if flag == LOWER:
        alpha = max(alpha, v)
    else:  # UPPER
        beta = min(beta, v)
    if alpha >= beta:
        return v, alpha, beta
    return None, alpha, beta


def tt_store(key, depth, value, flag):
    old = TT.get(key)
    if (old is None) or (old[0] <= depth):
        TT[key] = (depth, value, flag)


# ====== 手の順序付け（Move Ordering） ======
def move_order_score(board, turn, x, y, my_color):
    s = 0

    # 角は最優先
    if (x, y) in CORNERS:
        s += 200000

    # 角が空いてるときの X/C は危険なので下げる（局面依存は簡易に）
    if (x, y) in X_SQUARES:
        s -= 6000
    if (x, y) in C_SQUARES:
        s -= 2500

    nb = move(board, turn, x, y)

    # 相手の可動性を減らす方向
    opp = 3 - turn
    s += 35 * (len(get_legal_place(nb, turn)) - len(get_legal_place(nb, opp)))

    # 静的評価（雑に強い）
    s += evaluate_pos(nb, my_color)

    return s


# ====== 探索（αβ + TT + fail-soft） ======
def minimax(board, turn, my_color, depth, alpha, beta):
    if game_end(board):
        return evaluate_final(board, my_color)

    empties = count_empty(board)
    if empties <= ENDGAME_EMPTY:
        depth = INF  # 読み切り

    if depth == 0:
        return evaluate(board, my_color)

    key = board_key(board, turn)
    hit, alpha, beta = tt_probe(key, depth, alpha, beta)
    if hit is not None:
        return hit

    legal = get_legal_place(board, turn)
    if not legal:
        v = minimax(board, 3 - turn, my_color, depth - 1, alpha, beta)
        tt_store(key, depth, v, EXACT)
        return v

    # 順序付け
    legal.sort(key=lambda m: move_order_score(board, turn, m[0], m[1], my_color), reverse=True)

    alpha0, beta0 = alpha, beta

    if turn == my_color:
        value = -INF
        for x, y in legal:
            nb = move(board, turn, x, y)
            score = minimax(nb, 3 - turn, my_color, depth - 1, alpha, beta)
            if score > value:
                value = score
            if value > alpha:
                alpha = value
            if alpha >= beta:
                break
    else:
        value = INF
        for x, y in legal:
            nb = move(board, turn, x, y)
            score = minimax(nb, 3 - turn, my_color, depth - 1, alpha, beta)
            if score < value:
                value = score
            if value < beta:
                beta = value
            if alpha >= beta:
                break

    # TT 保存（fail-soft）
    if value <= alpha0:
        flag = UPPER
    elif value >= beta0:
        flag = LOWER
    else:
        flag = EXACT
    tt_store(key, depth, value, flag)

    return value


# ====== 本体（反復深化でさらに安定） ======
def myai(board, color):
    legal = get_legal_place(board, color)
    if not legal:
        return 0, 0

    # ルートも順序付け
    legal.sort(key=lambda m: move_order_score(board, color, m[0], m[1], color), reverse=True)

    best_move = legal[0]
    best_score = -INF

    # 反復深化：浅い結果を常に保持しつつ深くする（時間制限なし版）
    # 遅いなら MAX_DEPTH を下げる / ENDGAME_EMPTY を下げる
    for d in range(1, MAX_DEPTH + 1):
        local_best_move = best_move
        local_best_score = -INF

        for x, y in legal:
            nb = move(board, color, x, y)
            score = minimax(nb, 3 - color, color, d - 1, -INF, INF)
            if score > local_best_score:
                local_best_score = score
                local_best_move = (x, y)

        best_move = local_best_move
        best_score = local_best_score

        # 次の深さは、見つかった最善手を先頭にしてさらに枝刈り効かせる
        if best_move in legal:
            legal.remove(best_move)
            legal.insert(0, best_move)

    return best_move


myai.face = lambda: "🐬"
