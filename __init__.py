from sakura import othello

INF = 10 ** 9
SIZE = 6  # 盤面のサイズ
MOBILITY_WEIGHT = 5
MAX_DEPTH = 8

# 重み
WEIGHTS = [
    [100, -20, 10, 10, -20, 100],
    [-20, -50, -2, -2, -50, -20],
    [10,  -2,  5,  5,  -2, 10],
    [10,  -2,  5,  5,  -2, 10],
    [-20, -50, -2, -2, -50, -20],
    [100, -20, 10, 10, -20, 100],
]


# 自分の石を置ける場所をリストで返す
def get_legal_place(board, color):
    legal = []
    for y in range(SIZE):
        for x in range(SIZE):
            if othello.can_place_x_y(board, color, x, y):
                legal.append((x, y))
    return legal


# コピーした盤面で石を動かす関数
def move(board, color, x, y):
    copyBoard = othello.copy(board)
    othello.move_stone(copyBoard, color, x, y)
    return copyBoard


# 盤面を評価して自分と敵の差を返す
def evaluate(board, my_color):
    opp = 3 - my_color  # 敵の色

    my_score = 0
    opp_score = 0

    for y in range(SIZE):
        for x in range(SIZE):
            v = board[y][x]
            wgt = WEIGHTS[y][x]
            if v == my_color:
                my_score += wgt
            elif v == opp:
                opp_score += wgt

    return my_score - opp_score


def evaluate_final(board, my_color):
    opp = 3 - my_color
    my_stones  = 0
    opp_stones = 0

    for row in board:
        my_stones  += row.count(my_color)
        opp_stones += row.count(opp)

    diff = my_stones - opp_stones

    return diff * 1000  # 勝ち負け優先なので倍率高め


def evaluate_mobility(board, my_color):
    base_score = evaluate(board, my_color)

    my_moves  = len(get_legal_place(board, my_color))
    opp_moves = len(get_legal_place(board, 3 - my_color))

    mobility = my_moves - opp_moves

    return base_score + MOBILITY_WEIGHT * mobility


# 置ける場所がなければゲーム終了
def game_end(board):
    if get_legal_place(board, 1): return False
    if get_legal_place(board, 2): return False
    return True


def minimax(board, turn, color, depth, alpha, beta):
    legal = get_legal_place(board, turn)

    # 終局の場合、石の数の評価で返す
    if game_end(board): return evaluate_final(board, color)

    # 深さ0または終局の場合、評価だけ返す
    if depth == 0: return evaluate_mobility(board, color)

    # 打てる場所がない場合
    if not legal: return minimax(board, 3 - turn, color, depth - 1, alpha, beta)

    # 自分の番
    if turn == color:
        value = -INF
        for x, y in legal:
            next_board = move(board, turn, x, y)
            score = minimax(next_board, 3 - turn, color, depth - 1, alpha, beta)

            if score > value: value = score  # 最大値を更新
            if value > alpha: alpha = value  # αを更新
            if alpha >= beta: break  # α >= β になったら枝刈り

        return value

    # 相手の番
    else:
        value = INF
        for x, y in legal:
            next_board = move(board, turn, x, y)
            score = minimax(next_board, 3 - turn, color, depth - 1, alpha, beta)

            if score < value: value = score  # 最小値を更新
            if value < beta: beta = value  # βを更新
            if alpha >= beta:  break # α >= β になったら枝刈り

        return value


def myai(board, color):
    legal = get_legal_place(board, color)

    # 置き場がないとき
    if not legal: return 0, 0

    best_place = None
    best_score = -INF

    for x, y in legal:
        next_board = move(board, color, x, y)
        score = minimax(next_board, 3 - color, color, MAX_DEPTH - 1, -INF, INF)
        if score > best_score:
            best_score = score
            best_place = (x, y)

    return best_place

myai.face = lambda: "🐬"