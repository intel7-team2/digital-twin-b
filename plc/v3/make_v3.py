"""v3 래더(radder_v2.md 규칙) 생성: M 스텝 릴레이 · MC 없음 · 역순 배치 · 출력부 분리.
{이름} = 스텝 릴레이(아래 STEPS로 배정). 출력: ladder_mnemonic_v3.txt · IL 텍스트 · 스텝 추정표.
사용: py -3.12 make_v3.py"""
import io, os, re
H = os.path.dirname(os.path.abspath(__file__))
STEPS = {}


def seg(start, names):
    for k, n in enumerate(names.split()):
        if n != "-": assert n not in STEPS, n; STEPS[n] = start + k


# 15 RFID 실행기 · 입고 컨베이어
seg(1570, "R1_0 R1_1 R1_2 R1_3 R1_4 R2_0 R2_1 R2_2 R2_3 R2_4 R3_0 R3_1 R3_2 R3_3 R3_4 I0 I10 I15 I20 I30 I40")
# 16 턴테이블 TT1 · TTM
seg(1673, "T0 T10 T20 T30 T31 T32 T40 T41 T42 T50 M0 M10 M20 M30 M31 M32 M50")
# 17 합류(TT5) · 메인 검사 (TT3은 19 빈자리)
seg(1970, "P0 P10 P20 P30 P31 P32 - - - P50")
seg(1733, "Q0 Q10 Q20 - Q30 Q31 Q40 Q45 Q50 Q51")
seg(1770, "J10 J11 J12 J13 J40 J41 J42 J43 J44 - - - J0 J14 J20 J30 J45 J46 J50 J51 J60 J65 J70")
# 18(빈 구역) 투입 · 크레인 · 격리 기록 · 재검사 · TT2
seg(1810, "C0 C5 C10 C15 C16 C30 C31 - - - C20 C21 C22 C23 C24 C25 C26 C27 C28 C29 - -")
seg(1836, "A0 A1 A10 A11 A12 A20 A21 A30 A31 A32 A40 A41 B0 B1 B10 B11 B20 B21 B22 B30 B31 B41 B42 B43 G0 G10 G20")
seg(1863, "N10 N11 N12 N13 N14 - - - N41 N42 N43 N44 N0 N15 N16 N20 N30 N45 N46 N50 N51 N55 N60 K0 K10 K20 K30 - K32 K40 K41 K42 K50")
# ----- 2층: E 엘리베이터 · H 박스 벨트 · U 픽앤플레이스(NG 박스는 NG 벨트, GOOD은 박스 벨트에 놓음) · L 팔레타이저
seg(1985, "E0 E10 E11 E20 E30 E40 E41 E50 H0 H10 H20 H30 H31 H40 H41")
seg(1591, "U0 U10 U20 U21 U22 U23 U24 U25 U26"); seg(1743, "U27 U28 U29")
seg(1691, "L0 L1 L2 L3 L4 L10 L20 L21 L22"); seg(1712, "L30 - L32 L33 L34 L35 L36 L37")
RESET = [(1985, 15), (1591, 9), (1743, 3), (1691, 9), (1712, 8), (1570, 21), (1673, 17), (1733, 10), (1770, 23), (1810, 22), (1836, 27), (1863, 33), (1970, 10)]
for n, v in STEPS.items(): assert any(a <= v < a + c for a, c in RESET), n
INIT = [n for n in STEPS if re.fullmatch(r"(R\d_0|[A-Z]0)", n)]
# 11-26: 스텝 밖의 기억 비트(구간 점유 · 판정 넘김 · RFID 요청 · 알람 · 운전)와 내부 카운트도 초기화에서 지움
# (시뮬레이터 STOP → RUN은 M · D를 지우지 않아, 스텝만 지우면 M1984 같은 점유 비트가 남아 다음 회차가 멈춤)
FLAGS = "BKRST M1542 K6 | BKRST M1555 K3 | BKRST M1565 K3 | BKRST M1670 K3 | BKRST M1746 K19 | BKRST M1951 K8 | BKRST M1980 K5 | RST M1510 | RST M1950 | MOV K0 D1655 | MOV K0 D1918"


def rfid(k, base, tb, req, exe, gate):
    """base = D1510/1520/1530, req = M1545/55/65, tb = 첫 타이머 번호"""
    cid, w0, w1 = f"D{base+3}", f"D{req+1}", f"D{req+2}"
    s = lambda n: "{R%d_%d}" % (k, n)
    p = f"B{(k-1)*2}"
    return f"""{p}1  LD {s(4)} | AND M1950  =>  OUT T{tb+3} K5 | AND T{tb+3} | RST {s(4)} | MPS | AND< {w1} K3 | SET {s(1)} | MPP | AND>= {w1} K3 | SET M{req+2} | SET {s(0)}
{p}2  LD {s(3)} | AND M1950  =>  OUT T{tb+2} K5 | AND T{tb+2} | SET M{req+1} | SET {s(0)} | RST {s(3)}
{p}3  LD {s(2)} | AND M1950  =>  OUT M{exe} | OUT T{tb+1} K50 | MPS | AND T{tb+1} | AND= {cid} {w0} | INC {w1} | SET {s(4)} | RST {s(2)} | MPP | AND<> {cid} {w0} | SET {s(3)} | RST {s(2)}
{p}4  LD {s(1)} | AND M1950  =>  OUT T{tb} K10 | AND T{tb} | MOV {cid} {w0} | SET {s(2)} | RST {s(1)}
{p}5  LD M{req+1} | OR M{req+2}  =>  RST M{req}
{p}6  LD {s(0)} | AND M{req}{gate} | AND M1950  =>  MOV K0 {w1} | SET {s(1)} | RST {s(0)}
"""


def table(p, n, lim0, lim90, fr, bk, beam, tw, te, plus, dec20, clear):
    """턴테이블(0°에서 받아 90°로 보냄): p = 스텝 머리글, plus = 40 스텝이 앞(+)으로 나가면 True"""
    s40, s30 = (fr, bk) if plus else (bk, fr)
    return f"""{n}01  LD {{{p}50}} | AND {lim0} | AND M1950  =>  SET {{{p}0}} | RST {{{p}50}}
{n}02  LD {{{p}32}} | ANI {s30} | LD {{{p}42}} | ANI {s40} | ORB | AND M1950  =>  OUT T{te} K15 | AND T{te} | {clear} | SET {{{p}50}} | RST {{{p}32}} | RST {{{p}42}}
{n}03  LD {{{p}41}} | AND {s40} | AND M1950  =>  SET {{{p}42}} | RST {{{p}41}}
{n}04  LD {{{p}31}} | AND {s30} | AND M1950  =>  SET {{{p}32}} | RST {{{p}31}}
{n}05  LD {lim90} | AND M1950  =>  MPS | AND {{{p}40}} | SET {{{p}41}} | RST {{{p}40}} | MPP | AND {{{p}30}} | SET {{{p}31}} | RST {{{p}30}}
{n}06  LD {{{p}20}} | AND M1950  =>  OUT T{tw} K15 | AND T{tw} | {dec20}
{n}07  LD {{{p}10}} | AND {fr} | AND M1950  =>  SET {{{p}20}} | RST {{{p}10}}
{n}08  LD {{{p}0}} | LDI {beam} | OR {fr} | ANB | AND {lim0} | AND M1950  =>  SET {{{p}10}} | RST {{{p}0}}
"""


def gate(cmd, req, branches, last):
    parts = [f"AND {{{s}}} | " + " | ".join(o) for s, o in branches]
    if last: parts.append(last)
    out = ["MPS | " + parts[0]] + ["MRD | " + x for x in parts[1:-1]] + ["MPP | " + parts[-1]]
    return f"LDI M{req} | ANI M{req+1} | ANI M{req+2}  =>  " + " | ".join(out)


P = {}
P["COMMON"] = f"""; [초기화부] 첫 스캔, 또는 정지 중(M1950 OFF) 초기화 입력 M1961: 스텝 릴레이 · 구간 기억 비트 · 알람 리셋 → 초기 스텝 SET. 비상정지만으로는 유지(들고 있던 팔레트 낙하 방지). 랙 재고(D1660~)는 지우지 않음
; 11-26: 한 회로에 BKRST · SET 40여 개를 달면 GX Works2가 회로를 노랗게 표시(세로로 너무 긺) → 초기화 조건을 M1962(초기화 중)에 담고 작은 회로로 나눔
Z01  LD SM402 | LD M1961 | ANI M1950 | ORB  =>  OUT M1962
Z02  LD M1962  =>  {' | '.join(f'BKRST M{a} K{c}' for a, c in RESET[:7])}
Z03  LD M1962  =>  {' | '.join(f'BKRST M{a} K{c}' for a, c in RESET[7:])}
Z04  LD M1962  =>  {FLAGS}
Z05  LD M1962  =>  {' | '.join('SET {%s}' % n for n in INIT[:len(INIT)//2])}
Z06  LD M1962  =>  {' | '.join('SET {%s}' % n for n in INIT[len(INIT)//2:])}
; [공통]
A01  LDI X1500  =>  OUT M1500
A02  LD X1501 | ANI M1500  =>  SET M1950
A03  LDI X1502 | OR M1500  =>  RST M1950
A04  LD SM412  =>  PLS M1540
A05  LD M1540 | AND M1950  =>  INC D1540
A06  LD= D1540 K0 | OR> D1540 K32000  =>  MOV K1 D1540
A08  LD M1960 | OR X1503  =>  BKRST M1951 K8
; 11-26: 크레인 목표 칸은 보관용 D1603(A) · D1604(B)에 두고 운전 중에만 D1601 · D1602로 내보냄(CRANE D94 · D95, 정지 중 0 = 그 자리에 섬).
; 다시 시작할 때 도착 대기(A21 · A41 · B11 · B31)에 있던 크레인은 이동 시작 단계로 되돌림 — 이동 확인(또는 3초)을 다시 거쳐야 멈춰 선 것을 도착으로 보지 않음
A24  LDP M1950  =>  MPS | AND {{A0}} | MOV K55 D1603 | MRD | AND {{B0}} | MOV K55 D1604 | MRD | AND {{A21}} | SET {{A20}} | RST {{A21}} | MRD | AND {{A41}} | SET {{A40}} | RST {{A41}} | MRD | AND {{B11}} | SET {{B10}} | RST {{B11}} | MPP | AND {{B31}} | SET {{B30}} | RST {{B31}}
; [랙 스캔 · LOCK]
S01  LD SM400  =>  FMOV K0 D1690 K6 | MOV K32767 D1694 | MOV K0 Z0
S02  FOR K24
S03  LD= D1660Z0 K0 | AND= D1840Z0 K0  =>  MPS | AND< D1695 K3 | AND= D1690 K0 | MOV Z0 D1690 | INC D1690 | MPP | AND>= D1695 K3 | AND= D1691 K0 | MOV Z0 D1691 | INC D1691
S06  LD SM400  =>  - D1540 D1810Z0 D1696
S07  LD> D1660Z0 K0 | AND> D1810Z0 K0  =>  MPS | AND> D1840Z0 K0 | AND= D1692 K0 | MOV Z0 D1692 | INC D1692 | MPP | AND= D1840Z0 K0 | AND>= D1696 K16 | AND< D1810Z0 D1694 | MOV D1810Z0 D1694 | MOV Z0 D1693 | INC D1693
S08  LD> D1840Z0 K0 | AND= D1660Z0 K0  =>  MPS | AND M1540 | INC D1610Z0 | MPP | LD>= D1610Z0 K20 | OR M1961 | ANB | MOV K0 D1840Z0 | MOV K0 D1610Z0
S11  LD SM400  =>  INC D1695 | INC Z0
S12  LD>= D1695 K6  =>  MOV K0 D1695
S13  NEXT
; [발열 접수] 크레인 B가 그 칸을 꺼내는 중이면 운반 중 온도도 바꿈(접수 비트를 지우기 전에 봄)
H01  LD M1672  =>  MPS | AND= D1697 D1643 | ANI {{B0}} | ANI {{B1}} | MOV D1698 D1645 | MPP | AND>= D1697 K1 | AND<= D1697 K24 | MOV D1697 Z1 | DEC Z1 | MOV D1698 D1840Z1 | MOV K0 D1610Z1 | RST M1672
H02  LD<> D1692 K0 | OR M1671  =>  OUT M1690
"""
P["RFID"] = rfid(1, 1510, 1501, 1545, 1511, "") + rfid(2, 1520, 1505, 1555, 1521, " | AND {R3_0}") + rfid(3, 1530, 1509, 1565, 1531, " | AND {R2_0} | ANI M1555")
# RFID 작업 워드: D1546/47 · D1556/57 · D1566/67
c_prep1 = gate("C", 1545, [("C20", ["MOV K0 D1510", "MOV K0 D1511"]), ("C21", ["MOV K1 D1510", "MOV K0 D1511"]), ("C22", ["MOV K2 D1510", "MOV K0 D1511"]), ("C23", ["MOV K3 D1510", "MOV K0 D1511", "MOV D1516 D1512"]), ("C24", ["MOV K3 D1510", "MOV K1 D1511", "MOV D1542 D1512"])], None)
c_prep2 = gate("C", 1545, [("C25", ["MOV K3 D1510", "MOV K2 D1511", "MOV D1540 D1512"]), ("C26", ["MOV K3 D1510", "MOV K4 D1511", "MOV K0 D1512"]), ("C27", ["MOV K3 D1510", "MOV K5 D1511", "MOV K0 D1512"]), ("C28", ["MOV K3 D1510", "MOV K9 D1511", "MOV D1518 D1512"]), ("C29", ["MOV K2 D1510", "MOV K0 D1511"])], "AND<> K3M1820 K0 | SET M1545")
P["INFEED"] = f"""; [시퀀스] 역순
C01  LD {{C10}} | LD {{C31}} | AND X1510 | ORB | AND M1950  =>  OUT T1514 K30
C02  LD {{C31}} | AND T1514  =>  SET {{C0}} | RST {{C31}}
C03  LD {{C30}} | ANI M1542  =>  MOV D1516 D1543 | MOV D1518 D1544 | SET M1542 | RST M1510 | SET {{C31}} | RST {{C30}}
C04  LD M1547  =>  BKRST M1820 K10 | SET {{C16}}
C05  LD M1546 | AND {{C29}}  =>  RST {{C29}} | MPS | AND= D1515 D1516 | SET {{C30}} | MPP | AND<> D1515 D1516 | SET {{C16}}
C06  LD M1546  =>  MPS | AND {{C28}} | SET {{C29}} | RST {{C28}} | MRD | AND {{C27}} | SET {{C28}} | RST {{C27}} | MRD | AND {{C26}} | SET {{C27}} | RST {{C26}} | MRD | AND {{C25}} | SET {{C26}} | RST {{C25}} | MRD | AND {{C24}} | SET {{C25}} | RST {{C24}} | MPP | AND {{C23}} | SET {{C24}} | RST {{C23}}
C07  LD M1546 | AND {{C22}}  =>  RST {{C22}} | MPS | AND= D1515 K0 | SET {{C23}} | MPP | AND<> D1515 K0 | SET {{C16}}
C08  LD M1546  =>  MPS | AND {{C21}} | MOV D1515 D1517 | SET {{C22}} | RST {{C21}} | MPP | AND {{C20}} | SET {{C21}} | RST {{C20}}
C09  LD {{C16}}  =>  SET M1952 | SET {{C15}} | RST {{C16}}
C10  LD {{C15}} | LD M1960 | OR X1503 | ANB  =>  SET {{C10}} | RST {{C15}}
C11  LD {{C10}}  =>  RST M1543 | ANI X1511 | MOV K2 D1519
C12  LD {{C10}} | LD= D1519 K1 | AND= D1518 K4 | LD= D1519 K2 | AND= D1518 K6 | ORB | ANB  =>  SET M1543
C13  LD {{C10}} | AND T1514  =>  RST {{C10}} | MPS | AND M1543 | SET {{C20}} | MPP | ANI M1543 | SET M1951 | SET {{C15}}
C14  LD {{C5}} | AND M1950  =>  OUT T1513 K25 | MOV K1 D1519 | ANI X1510 | SET {{C10}} | RST {{C5}}
C15  LD {{C0}} | AND M1510 | AND X1510 | AND M1950  =>  SET {{C5}} | RST {{C0}}
C16  LD {{C0}} | OR {{C5}}  =>  MOV K2 D1509 | MPS | AND= D1518 K4 | MOV K2 D1508 | MPP | AND= D1518 K6 | MOV K4 D1508
C17  {c_prep1}
C18  {c_prep2}
C19  LD M1546 | OR M1547  =>  RST M1546 | RST M1547
; [출력부]
C90  LD {{C5}} | AND>= T1513 K15 | ANI T1513 | AND M1950  =>  OUT Y1500
C91  LD {{C0}} | OR {{C5}} | OR {{C31}} | LD {{C10}} | AND< T1514 K10 | ORB | ANI {{I15}} | LDI {{I20}} | OR X1513 | ANB | AND M1950  =>  OUT Y1501
C92  LDI {{C0}} | ANI {{C31}}  =>  OUT Y1502
"""
fork = lambda p, d, x, y, t, z: ""
P["CRANE"] = f"""; [입고 컨베이어] 역순
I01  LD {{I40}} | AND X1512 | AND M1950  =>  SET {{I0}} | RST {{I40}}
I02  LD {{I30}} | AND M1950  =>  OUTH T1538 K300 | AND T1538 | SET {{I40}} | RST {{I30}}
I03  LD {{I10}} | OR {{I15}} | OR {{I20}} | ANI X1512 | AND M1950  =>  SET {{I30}} | BKRST M1586 K3
I04  LD {{I10}} | OR {{I15}} | AND M1950  =>  OUT T1537 K52
I05  LD {{I15}} | AND T1537  =>  SET {{I20}} | RST {{I15}}
I06  LD {{I10}} | AND>= T1537 K12  =>  SET {{I15}} | RST {{I10}}
I07  LD {{I0}} | ANI X1513 | AND M1950  =>  SET {{I10}} | RST {{I0}}
; [크레인 A] 역순
D01  LD {{A41}} | ANI X1600 | ANI X1601 | AND M1950  =>  OUT T1540 K5 | AND T1540 | SET {{A0}} | RST {{A41}}
D02  LD {{A40}} | AND M1950  =>  MOV K55 D1603 | OUT T1518 K30 | LD X1600 | OR X1601 | OR T1518 | ANB | SET {{A41}} | RST {{A40}}
D03  LD {{A32}} | AND X1603 | AND M1950  =>  MOV D1540 D1810Z2 | RST M1542 | SET {{A40}} | RST {{A32}}
D04  LD {{A31}} | AND M1950  =>  OUT T1517 K80 | AND T1517 | ANI X1601 | SET {{A32}} | RST {{A31}}
D05  LD {{A30}} | AND X1604 | AND M1950  =>  SET {{A31}} | RST {{A30}}
D06  LD {{A21}} | ANI X1600 | ANI X1601 | AND M1950  =>  OUT T1539 K5 | AND T1539 | SET {{A30}} | RST {{A21}}
D07  LD {{A20}} | AND M1950  =>  / Z2 K6 D1870 | * D1870 K3 D1872 | + D1872 D1642 D1603 | OUT T1516 K30 | LD X1600 | OR X1601 | OR T1516 | ANB | SET {{A21}} | RST {{A20}}
D08  LD {{A12}} | AND X1603 | AND M1950  =>  SET {{A20}} | RST {{A12}}
D09  LD {{A11}} | AND M1950  =>  OUT T1515 K80 | AND T1515 | ANI X1601 | SET {{A12}} | RST {{A11}}
D10  LD {{A10}} | AND X1602 | AND M1950  =>  SET {{A11}} | RST {{A10}}
D11  LD {{A1}}  =>  MOV D1642 Z2 | DEC Z2 | MOV D1543 D1660Z2 | MOV K0 D1810Z2 | MOV D1642 D1600 | SET {{A10}} | RST {{A1}}
D12  LD {{A0}} | AND {{I40}} | AND M1542 | AND M1950  =>  MPS | AND<> D1690 K0 | LD= D1544 K4 | OR= D1691 K0 | ANB | MOV D1690 D1642 | MRD | AND<> D1691 K0 | LD= D1544 K6 | OR= D1690 K0 | ANB | MOV D1691 D1642 | MPP | LD<> D1690 K0 | OR<> D1691 K0 | ANB | SET {{A1}} | RST {{A0}}
; [크레인 B] 역순
E01  LD {{B43}} | AND X160B | AND M1950  =>  MOV D1644 D1646 | MOV D1645 D1647 | SET M1670 | SET {{B0}} | RST {{B43}}
E02  LD {{B42}} | AND M1950  =>  OUT T1522 K80 | AND T1522 | ANI X1609 | SET {{B43}} | RST {{B42}}
E03  LD {{B41}} | AND X160C | AND M1950  =>  SET {{B42}} | RST {{B41}}
E04  LD {{B31}} | ANI X1608 | ANI X1609 | AND X1610 | ANI M1670 | AND M1950  =>  OUT T1542 K5 | AND T1542 | SET {{B41}} | RST {{B31}}
E05  LD {{B30}} | AND M1950  =>  MOV K55 D1604 | OUT T1521 K30 | LD X1608 | OR X1609 | OR T1521 | ANB | SET {{B31}} | RST {{B30}}
E06  LD {{B22}} | AND X160B | AND M1950  =>  MOV K0 D1660Z3 | MOV K0 D1810Z3 | MOV K0 D1610Z3 | SET {{B30}} | RST {{B22}}
E07  LD {{B21}} | AND M1950  =>  OUT T1520 K80 | AND T1520 | ANI X1609 | SET {{B22}} | RST {{B21}}
E08  LD {{B20}} | AND X160A | AND M1950  =>  SET {{B21}} | RST {{B20}}
E09  LD {{B11}} | ANI X1608 | ANI X1609 | AND M1950  =>  OUT T1541 K5 | AND T1541 | SET {{B20}} | RST {{B11}}
E10  LD {{B10}} | AND M1950  =>  / Z3 K6 D1874 | * D1874 K3 D1876 | + D1876 D1643 D1604 | OUT T1519 K30 | LD X1608 | OR X1609 | OR T1519 | ANB | SET {{B11}} | RST {{B10}}
E11  LD {{B1}}  =>  MOV D1643 Z3 | DEC Z3 | MOV D1660Z3 D1644 | MOV D1840Z3 D1645 | MOV D1643 D1600 | SET {{B10}} | RST {{B1}} | MPS | AND= D1645 K0 | INC D1655 | MPP | AND<> D1645 K0 | SET M1671
E12  LD {{B0}} | AND M1950  =>  MPS | AND<> D1692 K0 | ANI M1671 | AND X1902 | MOV D1692 D1643 | SET {{B1}} | RST {{B0}} | MPP | LD= D1692 K0 | OR M1671 | ORI X1902 | ANB | AND<> D1693 K0 | ANI M1800 | AND< D1655 K2 | MOV D1693 D1643 | SET {{B1}} | RST {{B0}}
; [출력부] 속도 지령
I90  LD {{I20}} | AND M1950  =>  MOV K50 D1505 | MOV K50 D1506
I91  LDI {{I20}} | ORI M1950  =>  MOV K0 D1505
I92  LD {{I0}} | OR {{I10}} | AND M1950  =>  MOV K500 D1506
I93  LD {{I15}} | OR {{I30}} | OR {{I40}} | ORI M1950  =>  MOV K0 D1506
; [출력부] 크레인 — 포크 · 리프트는 정지 · 비상정지 중에도 자리 유지(들고 있던 팔레트 낙하 방지)라 M1950을 넣지 않음
D90  LDI {{A0}} | AND M1950  =>  OUT M1600
D91  LD {{A10}} | OR {{A11}}  =>  OUT Y1600
D92  LD {{A30}} | OR {{A31}}  =>  OUT Y1601
D93  LD {{A11}} | OR {{A12}} | OR {{A20}} | OR {{A21}} | OR {{A30}}  =>  OUT Y1602
E90  LDI {{B0}} | AND M1950  =>  OUT M1601
E91  LD {{B20}} | OR {{B21}}  =>  OUT Y1608
E92  LD {{B41}} | OR {{B42}}  =>  OUT Y1609
E93  LD {{B21}} | OR {{B22}} | OR {{B30}} | OR {{B31}} | OR {{B41}}  =>  OUT Y160A
D94  LD M1950  =>  MOV D1603 D1601 | MOV D1604 D1602
D95  LDI M1950  =>  MOV K0 D1601 | MOV K0 D1602
E94  LDI {{B41}} | ANI {{B42}} | ANI {{B43}} | AND M1950  =>  OUT Y1610
"""
P["SORT1"] = "; [시퀀스] TT1 역순 (40 = 격리: 롤(−) · 뒤 센서 / 30 = 메인: 롤(+) · 앞 센서)\n" + table("T", "F", "X1664", "X1668", "X1662", "X1663", "X1660", 1523, 1524, False,
    "MPS | AND= D1647 K0 | ANI M1753 | AND {M0} | SET {T30} | RST {T20} | MPP | AND<> D1647 K0 | AND X1902 | MOV D1646 D1648 | MOV D1647 D1649 | SET {T40} | RST {T20}", "RST M1670") + """; TTM 역순 (90°에서 받아 0°로 보냄)
F21  LD {M50} | AND X1669 | AND M1950  =>  SET {M0} | RST {M50}
F22  LD {M32} | ANI X1665 | AND M1950  =>  OUT T1547 K15 | AND T1547 | SET {M50} | RST {M32}
F23  LD {M31} | AND X1665 | AND M1950  =>  SET {M32} | RST {M31}
F24  LD {M30} | AND X1667 | AND M1950  =>  SET {M31} | RST {M30}
F25  LD {M20} | AND M1950  =>  OUT T1546 K15 | AND T1546 | ANI M1753 | SET {M30} | RST {M20}
F26  LD {M10} | AND X1665 | AND M1950  =>  SET {M20} | RST {M10}
F27  LD {M0} | LDI X1666 | OR X1665 | ANB | AND X1669 | AND M1950  =>  SET {M10} | RST {M0}
; 격리 기록 역순
G01  LD {G20} | AND= D1653 K0  =>  SET {G0} | RST {G20}
G02  LD {G10} | AND M1950  =>  OUT T1525 K100 | MPS | AND T1525 | SET M1957 | MPP | AND= D1653 K1 | MOV K0 D1650 | SET {G20} | RST {G10}
G03  LDF X1902  =>  RST M1671 | AND {G0} | MOV D1648 D1651 | MOV D1649 D1652 | MOV K1 D1650 | SET {G10} | RST {G0}
; [출력부] 회전은 정지 · 비상정지 중에도 각도 유지라 M1950을 넣지 않음
F90  LD {T0} | OR {T10} | ANI X1662 | LD {T31} | OR {T32} | ANI M1753 | ORB | AND M1950  =>  OUT Y1662
F91  LD {T41} | OR {T42} | AND M1950  =>  OUT Y1663
F92  LDI {T0} | ANI {T10} | ANI {T20} | ANI {T50}  =>  OUT Y1664
F93  LD {M0} | OR {M10} | ANI X1665 | LD {M31} | OR {M32} | ANI M1753 | ORB | AND M1950  =>  OUT Y1665
F94  LD {M0} | OR {M10} | OR {M20} | OR {M50}  =>  OUT Y1666
"""
j_prep1 = gate("J", 1555, [("J10", ["MOV K1 D1520", "MOV K0 D1521"]), ("J11", ["MOV K2 D1520", "MOV K0 D1521"]), ("J12", ["MOV K2 D1520", "MOV K4 D1521"]), ("J13", ["MOV K2 D1520", "MOV K9 D1521"])], None)
j_prep2 = gate("J", 1555, [("J40", ["AND= D1700 K2", "MOV K3 D1520", "MOV K4 D1521", "MOV D1527 D1522", "INC D1522"]), ("J41", ["MOV K3 D1520", "MOV K5 D1521", "MOV D1700 D1522"]), ("J42", ["MOV K3 D1520", "MOV K6 D1521", "MOV D1701 D1522"]), ("J43", ["MOV K3 D1520", "MOV K7 D1521", "MOV D1702 D1522"]), ("J44", ["MOV K3 D1520", "MOV K8 D1521", "MOV D1703 D1522"])], "LD<> K1M1770 K0 | OR<> K2M1774 K0 | ANB | SET M1555")
P["INSPECT"] = f"""; [시퀀스] 메인 검사 역순. M1755 = 태그를 못 읽음(0 · 직전 시리얼 · 남은 셀 수) → 3곳에서 씀
J01  LD {{J70}} | AND X1700 | AND M1950  =>  OUT T1528 K20 | AND T1528 | SET {{J0}} | RST {{J70}} | AND> D1655 K0 | DEC D1655
J02  LD {{J65}}  =>  SET M1750 | SET {{J70}} | RST {{J65}}
J03  LD {{J60}} | ANI M1750 | AND {{K0}} | LDI M1751 | ORI M1800 | ANB  =>  SET {{J65}} | RST {{J60}} | AND M1751 | SET M1754
J04  LD {{J51}}  =>  SET M1953 | SET M1752 | SET {{J50}} | RST {{J51}}
J05  LD {{J50}}  =>  SET {{J60}} | RST {{J50}} | LD M1752 | OR<> D1700 K1 | ANB | SET M1751
J06  LD {{J46}}  =>  SET M1953 | SET {{J45}} | RST {{J46}}
J07  LD {{J45}}  =>  MOV K0 D1710 | SET {{J50}} | RST {{J45}}
J08  LD M1557  =>  MPS | AND<> K2M1774 K0 | SET {{J46}} | BKRST M1774 K5 | MPP | AND<> K1M1770 K0 | SET {{J51}} | BKRST M1770 K4
J09  LD M1556  =>  MPS | AND {{J44}} | SET {{J45}} | RST {{J44}} | MRD | AND {{J43}} | SET {{J44}} | RST {{J43}} | MRD | AND {{J42}} | SET {{J43}} | RST {{J42}} | MPP | AND {{J41}} | SET {{J42}} | RST {{J41}}
J11  LD {{J30}} | AND M1950  =>  OUT M1700 | OUT T1527 K100 | MPS | AND T1527 | SET M1955 | MPP | AND= D1713 K1 | SET {{J40}} | RST {{J30}}
J10  LD {{J40}} | LD<> D1700 K2 | OR M1556 | ANB  =>  SET {{J41}} | RST {{J40}}
J12  LD {{J20}} | AND= D1713 K0  =>  MOV D1526 D1711 | MOV D1527 D1712 | MOV K1 D1710 | SET {{J30}} | RST {{J20}}
J13  LD {{J14}} | AND M1950  =>  OUT T1552 K10 | AND T1552 | SET {{J10}} | RST {{J14}}
J14  LD {{J10}} | LD= D1525 K0 | OR= D1525 D1558 | OR= D1525 D1714 | ANB | LD {{J11}} | AND= D1525 K0 | ORB | AND M1556  =>  OUT M1755
J15  LD M1755  =>  MPS | AND {{J11}} | MOV K0 D1526 | MPP | BKRST M1770 K2 | MPS | AND>= D1559 K2 | SET {{J51}} | MPP | AND< D1559 K2 | INC D1559 | SET {{J14}}
J16  LD M1556 | ANI M1755  =>  MPS | AND {{J13}} | MOV D1525 D1714 | SET {{J20}} | RST {{J13}} | MRD | AND {{J12}} | MOV D1525 D1527 | SET {{J13}} | RST {{J12}} | MRD | AND {{J11}} | MOV D1525 D1526 | SET {{J12}} | RST {{J11}} | MPP | AND {{J10}} | MOV D1525 D1558 | SET {{J11}} | RST {{J10}}
J17  LD {{J0}} | ANI X1700 | AND M1950  =>  OUT T1526 K10 | AND T1526 | RST M1751 | RST M1752 | MOV K0 D1559 | SET {{J10}} | RST {{J0}}
J18  {j_prep1}
J19  {j_prep2}
J20  LD M1556 | OR M1557  =>  RST M1556 | RST M1557
J21  LDI {{J0}} | ANI {{J70}}  =>  OUT M1753
""" + """; [시퀀스] TT2 역순 (30 = GOOD: 0°에서 그대로 직진 / 40 = 재검사: 90° 롤(+))
K01  LD {K50} | AND X1725 | AND M1950  =>  SET {K0} | RST {K50}
K02  LD {K32} | OR {K42} | ANI X1723 | AND M1950  =>  OUT T1544 K15 | AND T1544 | RST M1750 | RST M1754 | SET {K50} | RST {K32} | RST {K42}
K03  LD {K41} | AND X1723 | AND M1950  =>  SET {K42} | RST {K41}
K04  LD {K30} | AND X1723 | AND M1950  =>  SET {K32} | RST {K30}
K05  LD {K40} | AND X1726 | AND M1950  =>  SET {K41} | RST {K40}
K06  LD {K20} | AND M1950  =>  OUT T1543 K15 | AND T1543 | MPS | ANI M1754 | ANI M1984 | SET M1984 | SET M1980 | SET {K30} | RST {K20} | MPP | AND M1754 | ANI M1765 | SET {K40} | RST {K20}
K07  LD {K10} | AND X1723 | AND M1950  =>  SET {K20} | RST {K10}
K08  LD {K0} | LDI X1720 | OR X1723 | ANB | AND X1725 | AND M1950  =>  SET {K10} | RST {K0}
; [재검사 라인]
L01  LDF X1800  =>  INC D1800
L02  LDI X1800 | AND M1950  =>  OUT T1529 K30 | AND T1529 | OUT M1800
; [출력부] 스토퍼 · 회전은 정지 중에도 유지
K90  LD {K0} | OR {K10} | ANI X1723 | LD {K30} | OR {K32} | OR {K41} | OR {K42} | ORB | AND M1950  =>  OUT Y1722
K92  LD {K40} | OR {K41} | OR {K42}  =>  OUT Y1724
J90  LDI {J70}  =>  OUT Y1701
"""
n_prep1 = gate("N", 1565, [("N10", ["MOV K1 D1530", "MOV K0 D1531"]), ("N11", ["MOV K2 D1530", "MOV K0 D1531"]), ("N12", ["MOV K2 D1530", "MOV K4 D1531"]), ("N13", ["MOV K2 D1530", "MOV K5 D1531"]), ("N14", ["MOV K2 D1530", "MOV K9 D1531"])], None)
n_prep2 = gate("N", 1565, [("N41", ["MOV K3 D1530", "MOV K5 D1531", "MOV D1730 D1532"]), ("N42", ["MOV K3 D1530", "MOV K6 D1531", "MOV D1731 D1532"]), ("N43", ["MOV K3 D1530", "MOV K7 D1531", "MOV D1732 D1532"]), ("N44", ["MOV K3 D1530", "MOV K8 D1531", "MOV D1733 D1532"])], "LD<> K2M1863 K0 | OR<> K1M1871 K0 | ANB | SET M1565")
P["RETEST"] = f"""; [시퀀스] 재검사 역순. M1766 = 태그를 못 읽음
N01  LD {{N60}} | AND X1730 | AND M1950  =>  OUT T1532 K20 | AND T1532 | SET {{N0}} | RST {{N60}}
N02  LD {{N55}}  =>  SET M1760 | SET {{N60}} | RST {{N55}}
N03  LD {{N51}}  =>  SET M1954 | SET {{N50}} | RST {{N51}}
N04  LD {{N50}} | ANI M1760  =>  AND {{Q0}} | SET {{N55}} | RST {{N50}} | MPS | AND M1761 | SET M1764 | MPP | ANI M1761 | RST M1764
N05  LD {{N46}}  =>  SET M1954 | SET {{N45}} | RST {{N46}}
N06  LD {{N45}}  =>  MOV K0 D1740 | SET {{N50}} | RST {{N45}} | AND= D1730 K1 | SET M1761
N07  LD M1567  =>  MPS | AND<> K1M1871 K0 | SET {{N46}} | BKRST M1871 K4 | MPP | AND<> K2M1863 K0 | SET {{N51}} | BKRST M1863 K5
N08  LD M1566  =>  MPS | AND {{N44}} | SET {{N45}} | RST {{N44}} | MRD | AND {{N43}} | SET {{N44}} | RST {{N43}} | MRD | AND {{N42}} | SET {{N43}} | RST {{N42}} | MPP | AND {{N41}} | SET {{N42}} | RST {{N41}}
N09  LD {{N30}} | AND M1950  =>  OUT M1730 | OUT T1531 K100 | MPS | AND T1531 | SET M1956 | MPP | AND= D1743 K1 | SET {{N41}} | RST {{N30}}
; 11-27(A22): RETEST 팩은 재검사기 정위치 스토퍼에서 20초 세운 뒤(정치 · 전압 안정) 계측 요청. 메인 NG 팩은 계측 없이 통과(N12에서 N20을 안 거침)
N10  LD {{N20}} | AND= D1743 K0 | AND M1950  =>  OUT T1583 K200 | AND T1583 | MOV D1536 D1741 | MOV D1537 D1742 | MOV K1 D1740 | SET {{N30}} | RST {{N20}}
N11  LD {{N16}} | AND M1950  =>  OUT T1553 K10 | AND T1553 | SET {{N10}} | RST {{N16}}
N12  LD {{N15}}  =>  RST {{N15}} | MPS | AND< D1761 K2 | SET {{N51}} | MRD | AND= D1761 K2 | SET {{N20}} | MPP | AND> D1761 K2 | SET {{N50}}
N13  LD {{N10}} | LD= D1535 K0 | OR= D1535 D1568 | OR= D1535 D1744 | ANB | LD {{N11}} | AND= D1535 K0 | ORB | AND M1566  =>  OUT M1766
N14  LD M1766  =>  MPS | AND {{N11}} | MOV K0 D1536 | MPP | BKRST M1863 K2 | MPS | AND>= D1569 K2 | SET {{N51}} | MPP | AND< D1569 K2 | INC D1569 | SET {{N16}}
N15  LD M1566 | ANI M1766  =>  MPS | AND {{N14}} | MOV D1535 D1744 | SET {{N15}} | RST {{N14}} | MRD | AND {{N13}} | MOV D1535 D1761 | SET {{N14}} | RST {{N13}} | MRD | AND {{N12}} | MOV D1535 D1537 | SET {{N13}} | RST {{N12}} | MRD | AND {{N11}} | MOV D1535 D1536 | SET {{N12}} | RST {{N11}} | MPP | AND {{N10}} | MOV D1535 D1568 | SET {{N11}} | RST {{N10}}
N16  LD {{N0}} | ANI X1730 | AND M1950  =>  OUT T1530 K10 | AND T1530 | RST M1761 | MOV K0 D1569 | SET {{N10}} | RST {{N0}} | AND> D1800 K0 | DEC D1800
N17  {n_prep1}
N18  {n_prep2}
N19  LD M1566 | OR M1567  =>  RST M1566 | RST M1567
N20  LDI {{N0}} | ANI {{N60}}  =>  OUT M1765
""" + """; [시퀀스] TT3 역순 (모두 90° 롤(−)로 합류 레일)
P01  LD {P50} | AND X1735 | AND M1950  =>  SET {P0} | RST {P50}
P02  LD {P32} | ANI X1734 | AND M1950  =>  OUT T1534 K15 | AND T1534 | RST M1760 | SET {P50} | RST {P32}
P04  LD {P31} | AND X1734 | AND M1950  =>  SET {P32} | RST {P31}
P05  LD {P30} | AND X1737 | AND M1950  =>  SET {P31} | RST {P30}
P06  LD {P20} | AND M1950  =>  OUT T1533 K15 | AND T1533 | AND {Q0} | SET {P30} | RST {P20}
P07  LD {P10} | AND X1733 | AND M1950  =>  SET {P20} | RST {P10}
P08  LD {P0} | LDI X1731 | OR X1733 | ANB | AND X1735 | AND M1950  =>  SET {P10} | RST {P0}
; [시퀀스] TT5 합류 역순. M1984 = E1 앞 구간에 팩 1개(GOOD 직진 · 재검사 합류가 번갈아), M1980 = 그 팩 GOOD
Q01  LD {Q51} | ANI X1904 | AND M1950  =>  OUT T1548 K15 | AND T1548 | SET {Q0} | RST {Q51}
Q02  LD {Q50} | AND X1904 | AND M1950  =>  SET {Q51} | RST {Q50}
Q03  LD {Q45} | AND X1907 | AND M1950  =>  SET {Q50} | RST {Q45}
Q04  LD {Q40} | AND M1950  =>  OUT T1545 K15 | AND T1545 | SET {Q45} | RST {Q40}
Q05  LD {Q31} | AND X1905 | AND M1950  =>  SET {Q40} | RST {Q31}
Q06  LD {Q30} | AND X1908 | AND M1950  =>  SET {Q31} | RST {Q30}
Q08  LD {Q20} | ANI M1984 | AND M1950  =>  SET M1984 | SET {Q30} | RST {Q20} | MPS | AND M1764 | SET M1980 | MPP | ANI M1764 | RST M1980
Q09  LD {Q10} | AND X1736 | AND M1950  =>  SET {Q20} | RST {Q10}
Q10  LD {Q0} | LD {P31} | OR {P32} | ANB | AND M1950  =>  SET {Q10} | RST {Q0}
; [출력부] 스토퍼 · 회전은 정지 중에도 유지
P90  LD {P0} | OR {P10} | ANI X1733 | AND M1950  =>  OUT Y1733
P91  LD {P31} | OR {P32} | AND M1950  =>  OUT Y1734
P92  LD {P30} | OR {P31} | OR {P32}  =>  OUT Y1735
Q90  LD {Q10} | OR {Q31} | AND M1950  =>  OUT Y1736
Q91  LDI {Q30} | ANI {Q31} | ANI {Q40} | ANI {Q45} | AND M1950  =>  OUT Y1904
Q92  LD {Q31} | ANI X1905 | AND M1950  =>  OUT Y1906
Q93  LD {Q30} | OR {Q31} | OR {Q40}  =>  OUT Y1905
N90  LDI {N60}  =>  OUT Y1730
"""
P["DRIVE"] = """; [1층 컨베이어]
V01  LD M1950  =>  OUT Y1611 | OUT Y1690 | OUT Y1702 | OUT Y1703 | OUT Y191D | MPS | ANI M1753 | OUT Y1700 | MPP | ANI M1765 | OUT Y1800
; [E1 엘리베이터] 역순. X1911 · X1912 = 입구 · 안쪽(트임 ON), M1981 = 실린 팩 GOOD
X01  LD {E50} | AND X1913 | AND M1950  =>  OUT T1556 K15 | AND T1556 | SET {E0} | RST {E50}
X02  LD {E41} | AND X1911 | AND M1950  =>  OUT T1557 K15 | AND T1557 | SET {E50} | RST {E41}
X03  LD {E40} | ANI X1911 | AND M1950  =>  SET {E41} | RST {E40}
X04  LD {E30} | AND X1916 | AND {U0} | AND M1950  =>  OUT T1558 K15 | AND T1558 | SET {E40} | SET {U10} | RST {E30} | RST {U0} | MPS | AND M1981 | SET M1982 | MPP | ANI M1981 | RST M1982
X05  LD {E20} | AND M1950  =>  OUT T1559 K20 | AND T1559 | SET {E30} | RST {E20}
X06  LD {E11} | AND X1911 | AND M1950  =>  SET {E20} | RST M1984 | RST {E11} | MPS | AND M1980 | SET M1981 | MPP | ANI M1980 | RST M1981
X07  LD {E10} | ANI X1911 | AND M1950  =>  SET {E11} | RST {E10}
X08  LD {E0} | AND X1910 | AND M1950  =>  SET {E10} | RST {E0}
; [픽앤플레이스] 역순. D1910~12 = SP X · Y · Z, D1913~15 = 현재. 11-26: 상자 크기를 넘기지 않고 얕게(L 750) 먼저 내려 상자 감지 X1918이 없으면 깊게(M 980) 내림(RFID를 못 읽은 팩도 집음, L 상자에 부딪히지 않음). 11-26 실측(높이 36): 집기 Z M 980 · L 750(감지 지점 +24 · +34), 놓기 = 집기 − 516(벨트 면이 팔레트 면보다 506 높음), X1918(상자 감지) 켜져야 들어 올림
U01  LD {U28} | ANI X1917 | AND M1950  =>  OUT T1560 K30 | AND T1560 | SET {U0} | RST {U28}
U02  LD {U27} | AND<= D1915 K10 | AND M1950  =>  SET {U28} | SET {H10} | RST {H0} | RST {U27} | MPS | AND M1982 | SET M1983 | MPP | ANI M1982 | RST M1983
U03  LD {U26} | AND M1950  =>  OUT T1561 K10 | AND T1561 | SET {U27} | RST {U26} | ANI M1982 | INC D1901
U04  LD {U25} | AND M1950  =>  OUT T1562 K30 | AND T1562 | SET {U26} | RST {U25}
U05  LD {U24} | AND>= D1913 K985 | AND {H0} | AND M1950 | LD M1982 | AND<= D1914 K324 | LDI M1982 | AND>= D1914 K947 | ORB | ANB  =>  SET {U25} | RST {U24}
U06  LD {U23} | AND<= D1915 K10 | AND M1950  =>  SET {U24} | RST {U23}
U07  LD {U22} | AND X1918 | AND M1950  =>  OUT T1563 K10 | AND T1563 | SET {U23} | RST {U22}
U08  LD {U21} | AND>= D1915 K740 | AND M1950  =>  OUT T1577 K15 | AND T1577 | MPS | AND X1918 | SET {U22} | RST {U21} | MPP | ANI X1918 | MOV K980 D1917 | SET {U29} | RST {U21}
U11  LD {U29} | AND>= D1915 K970 | AND M1950  =>  OUT T1580 K15 | AND T1580 | SET {U22} | RST {U29}
U09  LD {U20} | AND>= D1913 K315 | AND<= D1913 K335 | AND>= D1914 K326 | AND<= D1914 K346 | AND<= D1915 K10 | AND M1950  =>  SET {U21} | RST {U20} | MOV K750 D1917
U10  LD {U10} | AND X1917 | AND M1950  =>  OUT T1564 K30 | AND T1564 | SET {U20} | RST {U10}
; [박스 벨트] 역순. M1983 = 방금 놓은 박스 GOOD(NG 박스는 NG 벨트가 바로 가져감)
Y03  LD {H31} | AND X1900 | AND M1950  =>  OUT T1565 K40 | AND T1565 | SET {H0} | RST {L10} | RST {H31} | INC D1918 | MPS | AND>= D1918 K2 | SET {L20} | MPP | AND< D1918 K2 | SET {L10}
Y04  LD {H30} | ANI X1900 | AND M1950  =>  SET {H31} | RST {H30}
Y05  LD {H10} | AND M1950  =>  MPS | AND M1983 | AND {L10} | SET {H30} | RST {H10} | MPP | ANI M1983 | SET {H0} | RST {H10}
; 11-27: 박스 벨트에서 상자가 30초 넘게 빔(X1900)을 지나지 못하면 알람 M1958(상자 걸림). 상자를 바로 놓고 리셋 → 이어서 진행
Y06  LD {H30} | OR {H31} | AND M1950  =>  OUT T1582 K300 | AND T1582 | SET M1958
; [팔레타이저] 역순. D1918 = 올린 박스 수(2개면 배출)
; 11-27: 상자 1개만 실린 채 2층(엘리베이터 · 픽앤플레이스 · 박스 벨트)이 6분 동안 비어 있으면 그대로 배출(배치 끝 홀수 GOOD 상자가 다음 배치와 섞이지 않게).
; 6분 = 투입 간격 최대 약 2분 × 3. 실제 PLC 5회차에서 2층 상자 사이 최대 268초(격리 · 재검사 팩이 겹칠 때) + 재검사 대기 20초 → 약 290초보다 여유
O17  LD {L10} | AND= D1918 K1 | AND {H0} | AND {U0} | AND {E0} | AND M1950  =>  OUT T1581 K3600 | AND T1581 | SET {L20} | RST {L10}
O01  LD {L37} | AND X1925 | AND M1950  =>  OUT T1567 K30 | AND T1567 | MOV K0 D1918 | SET {L0} | RST {L37}
O02  LD {L36} | ANI X1925 | AND M1950  =>  SET {L37} | RST {L36}
O03  LD {L35} | AND M1950  =>  OUT T1568 K50 | AND T1568 | SET {L36} | RST {L35}
O04  LD {L34} | AND M1950  =>  OUT T1569 K70 | AND T1569 | SET {L35} | RST {L34}
O05  LD {L33} | AND M1950  =>  OUT T1570 K20 | AND T1570 | SET {L34} | RST {L33}
O06  LD {L32} | AND M1950  =>  OUT T1571 K50 | AND T1571 | SET {L33} | RST {L32}
O08  LD {L30} | AND M1950  =>  OUT T1572 K10 | AND T1572 | SET {L32} | RST {L30}
O09  LD {L22} | AND X1923 | AND M1950  =>  OUT T1573 K30 | AND T1573 | SET {L30} | RST {L22}
O10  LD {L21} | AND M1950  =>  OUT T1578 K30 | LD X1923 | OR T1578 | ANB | SET {L22} | RST {L21}
O11  LD {L20} | ANI X1923 | AND M1950  =>  SET {L21} | RST {L20}
O12  LD {L4} | ANI X1922 | AND M1950  =>  OUT T1574 K10 | AND T1574 | SET {L10} | RST {L4}
O13  LD {L3} | AND X1922 | AND M1950  =>  SET {L4} | RST {L3}
O14  LD {L2} | AND M1950  =>  OUT T1575 K20 | AND T1575 | SET {L3} | RST {L2}
O15  LD {L1} | AND X1921 | AND M1950  =>  SET {L2} | RST {L1}
O16  LD {L0} | AND M1950  =>  MOV K2 D1916 | OUT T1576 K20 | AND T1576 | SET {L1} | RST {L0}
; [출력부] 엘리베이터
X90  LD M1984 | LDI X1910 | OR {E10} | OR {E11} | ANB | AND M1950  =>  OUT Y1910
X91  LDI {E10} | ANI {E11}  =>  OUT Y1911
X92  LD {E10} | OR {E11} | AND M1950  =>  OUT Y1912
X93  LD {E40} | OR {E41} | AND M1950  =>  OUT Y1913
X94  LD {E30} | ANI X1916 | AND M1950  =>  OUT Y1914
X95  LD {E50} | ANI X1913 | AND M1950  =>  OUT Y1915
; [출력부] 2층 팔레트 · 픽앤플레이스(잡기는 정지 중에도 유지)
U90  LD {U10} | AND M1950  =>  OUT Y1916
U91  LD {U10} | OR {U28} | AND M1950  =>  OUT Y1917
U92  LDI {U28}  =>  OUT Y1918
U93  LD M1950  =>  OUT Y1919
U94  LD {U22} | OR {U23} | OR {U24} | OR {U25}  =>  OUT Y191A
U95  LDI M1950  =>  BMOV D1913 D1910 K3
U96  LD M1950  =>  MPS | LD {U24} | OR {U25} | OR {U26} | OR {U27} | ANB | MOV K1000 D1910 | MOV K957 D1911 | AND M1982 | MOV K314 D1911 | MRD | LDI {U24} | ANI {U25} | ANI {U26} | ANI {U27} | ANB | MOV K325 D1910 | MOV K336 D1911 | MRD | LD {U21} | OR {U29} | OR {U22} | ANB | MOV D1917 D1912 | MRD | LD {U25} | OR {U26} | ANB | - D1917 K516 D1912 | MPP | LDI {U21} | ANI {U29} | ANI {U22} | ANI {U25} | ANI {U26} | ANB | MOV K0 D1912
; [출력부] 박스 벨트 · 팔레타이저(집게 · 판은 정지 중에도 유지)
Y91  LD {H30} | OR {H31} | AND M1950  =>  OUT Y1920
Y92  LD {H30} | OR {H31} | AND M1950  =>  OUT Y191B | OUT Y191C
O90  LD {L20} | OR {L21} | AND M1950  =>  OUT Y1921
O91  LD {L30} | OR {L32}  =>  OUT Y1922
O92  LD {L32} | OR {L33} | OR {L34}  =>  OUT Y1923
O93  LD {L3} | OR {L4} | AND M1950  =>  OUT Y1924
O94  LD {L34} | AND M1950  =>  OUT Y1925
O95  LD {L2} | OR {L3} | OR {L4} | OR {L33} | OR {L34} | AND M1950  =>  OUT Y1926
O96  LD {L1} | OR {L36} | OR {L37} | AND M1950  =>  OUT Y1927
O97  LD {L1} | AND M1950  =>  OUT Y1928
O98  LD {L36} | OR {L37} | AND M1950  =>  OUT Y1929
O99  LD {L0} | AND>= T1576 K10 | AND M1950  =>  OUT Y192A
"""
P["COUNTER"] = """R01  LDF X1900  =>  INC D1900
R03  LDF X1902  =>  INC D1902
R04  LD SM400  =>  + D1900 D1901 D1990 | + D1990 D1902 D1903 | MOV D1903 D1994 | MOV K0 D1995
R05  LD<> D1903 K0  =>  * D1900 K1000 D1992 | D/ D1992 D1994 D1996 | MOV D1996 D1904
R06  LD= D1903 K0  =>  MOV K0 D1904
R07  LD M1920 | OR T1579  =>  FMOV K0 D1900 K5
R08  LD X1503  =>  OUT T1579 K20
"""
P["LAMP"] = """W01  LD M1690  =>  OUT Y1691 | OUT Y1694
W02  LD M1800 | OR<> K2M1951 K0  =>  OUT Y1692
W03  LD M1950  =>  OUT Y1693
; 11-27: HMI 알람 확인 M1960 · 카운터 리셋 M1920은 '비트 셋' 스위치 — 한 스캔 쓰인 뒤 여기(마지막 프로그램)서 끔(MX OPC 경유 짧은 펄스가 빠지는 것 방지)
W04  LD M1960  =>  RST M1960
W05  LD M1920  =>  RST M1920
W06  LD M1961  =>  RST M1961
; 11-27: HMI '알람 발생 중' 표시 비트(HMI 알람 블록 1에 있는 조건 전부)
W07  LD M1500 | OR M1800 | OR M1690 | OR<> K2M1951 K0  =>  OUT M1959
"""


def est(ins):
    t = ins.split(); op, a = t[0], t[1:]
    idx = sum(1 for x in a if re.search(r"\dZ\d", x))
    if op in ("LD", "LDI", "AND", "ANI", "OR", "ORI", "ANB", "ORB", "MPS", "MRD", "MPP", "NEXT"): n = 1
    elif op in ("LDP", "LDF", "ANDP", "ANDF", "ORP", "ORF"): n = 2
    elif re.match(r"(LD|AND|OR)[<>=]", op): n = 3
    elif op in ("OUT", "OUTH"): n = 4 if a[0][0] == "T" else 1
    elif op in ("SET", "RST"): n = 1
    elif op in ("MOV", "INC", "DEC", "FOR", "PLS"): n = 2
    elif op in ("+", "-", "*", "/", "D/"): n = 4
    elif op in ("FMOV", "BMOV"): n = 4
    elif op in ("BKRST",): n = 3
    else: raise ValueError(ins)
    return n + idx


def main():
    used = {}
    txt = ["; Project B v6 래더 v3 명령어 목록 (plc/v2/make_v3.py가 만듦 · 규칙 radder_v2.md)", ""]
    il, rows, tot = [], [], {}
    for prog, body in P.items():
        txt += [f"; @PROGRAM {prog}"]; il += [f"; ===== {prog} ====="]
        for line in body.rstrip("\n").split("\n"):
            line = re.sub(r"\{(\w+)\}", lambda m: f"M{STEPS[m.group(1)]}", line)
            m = re.match(r"^([A-Z]\d\d)\s+(.*)$", line)
            txt.append(line)
            if not m: continue
            assert (prog, m.group(1)) not in used and m.group(1) not in {k[1] for k in used}, m.group(1); used[(prog, m.group(1))] = 1
            ins = [x.strip() for x in re.split(r"\||=>", m.group(2)) if x.strip()]
            il += ins; s = sum(est(i) for i in ins); rows.append((prog, m.group(1), len(ins), s)); tot[prog] = tot.get(prog, 0) + s
        txt.append(""); il += ["END", ""]
    io.open(os.path.join(H, "ladder_mnemonic_v3.txt"), "w", encoding="utf-8", newline="\n").write("\n".join(txt) + "\n")
    io.open(os.path.join(H, "ladder_v3_IL.txt"), "w", encoding="utf-8", newline="\n").write("\n".join(x for x in il if True) + "\n")
    md = ["# v3 래더 렁별 명령어 수 · 스텝 추정치", "", "> 스텝은 **추정치**(기본 명령 1 · 비교 3 · MOV/INC 2 · 타이머 4 등)이고 실제 값은 GX Works2 변환 결과를 봅니다.", "", "| 프로그램 | 렁 | 명령어 수 | 스텝(추정) |", "|---|---|---|---|"]
    md += [f"| {a} | {b} | {c} | {d} |" for a, b, c, d in rows]
    md += ["", "| 프로그램 | 렁 수 | 스텝(추정, END 포함) |", "|---|---|---|"] + [f"| {p} | {sum(1 for r in rows if r[0]==p)} | {tot[p]+1} |" for p in P] + [f"| **합계** | {len(rows)} | {sum(tot.values())+len(P)} |"]
    io.open(os.path.join(H, "steps_v3.md"), "w", encoding="utf-8", newline="\n").write("\n".join(md) + "\n")
    st = ["# v3 스텝 릴레이 배정", "", "| 이름 | 번지 |", "|---|---|"] + [f"| {n} | M{v} |" for n, v in STEPS.items()]
    io.open(os.path.join(H, "steps_relay_v3.md"), "w", encoding="utf-8", newline="\n").write("\n".join(st) + "\n")
    # 검사: 이중 코일(OUT) · Y SET/RST · 스텝 M이 기존 번지와 겹침 · MC · 한 번만 참조되는 M
    outs, refs = {}, {}
    for prog, body in P.items():
        for line in body.split("\n"):
            m = re.match(r"^([A-Z]\d\d)\s+(.*)$", line)
            if not m: continue
            for ins in [x.strip() for x in re.split(r"\||=>", m.group(2)) if x.strip()]:
                t = ins.split()
                if t[0] in ("OUT", "OUTH"): outs.setdefault(t[1], []).append(m.group(1))
                if t[0] in ("SET", "RST") and t[1][0] == "Y": print("Y SET/RST 금지", m.group(1), ins)
                if t[0] in ("MC", "MCR"): print("MC 금지")
                if t[0] not in ("OUT", "SET", "RST", "PLS", "BKRST"):
                    for a in t[1:]: refs[a] = refs.get(a, 0) + 1
    print("이중 코일", {k: v for k, v in outs.items() if len(v) > 1})
    print("한 번 이하로 참조되는 중간 M", sorted(k for k in outs if k[0] == "M" and refs.get(k, 0) < 2))
    lits = {int(x) for b in P.values() for x in re.findall(r"(?<![K\dA-Z])M(\d{4})", b)}
    rng = {x for a, c in RESET for x in range(a, a + c)}
    print("스텝 번지와 겹치는 기존 M", sorted(x for x in lits & rng if x not in {a for a, _ in RESET} | {1586, 1820, 1770, 1774, 1863, 1871}))
    print("렁", len(rows), "· 추정 스텝", {p: tot[p] + 1 for p in P}, "합계", sum(tot.values()) + len(P))


main()
