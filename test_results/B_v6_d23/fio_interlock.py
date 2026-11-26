"""현장 즉시정지 인터록(11-25) — 센서가 켜지는 순간 그 구동을 바로 끊음(중계 쪽 0.02초).
GX Simulator2 ↔ MX OPC 왕복이 1 ~ 3초 걸려 래더의 정지 명령만으로는 지나침. 동작 순서는 래더가 정하고 인터록은 '끊기'만 함.
센서 상승에서 끊고, 래더가 그 출력을 한 번 끄면 풀림(같은 자리에서 다시 내보낼 수 있게)."""
RULES = [("Y1662", ("X1664", "X1662")),   # TT1 · TTM · TT2 · TT3: 받는 각도에서 진행 쪽 끝 센서
         ("Y1665", ("X1669", "X1665")), ("Y1722", ("X1725", "X1723")), ("Y1733", ("X1735", "X1733")),
         ("Y1906", ("X1908", "X1905")),   # TT5(재검사 합류)
         ("Y1736", ("X1736",)),           # 합류 대기 레일
         ("Y1914", ("X1916",)), ("Y1915", ("X1913",)),   # E1 상승 = 2층 위 센서 · 하강 = 1층 아래 센서
         ("Y1927", ("X1921",))]           # 팔레타이저 팔레트 정위치
_prev, _cut = {}, set()
_arm = [False]


def cuts(bit, want):
    """bit(입력 이름) · want(출력 이름 = 래더가 바라는 값) → 지금 끊어야 하는 코일 이름 집합"""
    conds = {y: all((not bit(x[1:])) if x[0] == "!" else bit(x) for x in xs) for y, xs in RULES}
    # E1 받기: 1층에서 입구 센서(X1911, 트임 ON)를 가렸다 다시 트이면 팔레트가 다 올라온 것
    if not bit("X1913"): _arm[0] = False
    elif not bit("X1911"): _arm[0] = True
    conds["Y1912"] = bool(_arm[0] and bit("X1911"))
    for y, c in conds.items():
        if c and not _prev.get(y, c): _cut.add(y)
        _prev[y] = c
    for y in list(_cut):
        if not want(y): _cut.discard(y)
    return set(_cut)


# 입고점: 로딩 컨베이어 끝 빔이 가려지면(X1512 OFF = 팔레트 도착) 로딩 · 진입 롤러 속도를 0으로(늦게 서면 크레인 A가 기둥에 박음)
def zero_words(bit):
    return {"D1505", "D1506"} if not bit("X1512") else set()
