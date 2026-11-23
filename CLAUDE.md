# CLAUDE.md — Claude Code 지침

공통 지침은 AGENTS.md를 따릅니다.

@AGENTS.md

아래는 Claude Code에서 이 저장소를 다룰 때만 해당하는 내용입니다.

## 대화 · 보고

- 사용자와는 한국어로 대화합니다.
- 결과를 보고할 때는 무엇을 바꿨는지 · 무엇을 확인했는지(숫자) · 확인하지 못한 것을 나눠 적습니다. 시뮬레이션 결과와 실기 결과를 섞지 않습니다.
- 사용자가 결정해야 할 것은 `확인필요_및_논의사항.md`에 안건(A#)으로 남기고, 답에서도 따로 알려 줍니다.

## 환경

- Windows · OneDrive 폴더(`Dtwin_pj`). 셸은 Git Bash와 PowerShell을 둘 다 쓸 수 있습니다.
- Python 출력에 한글이 있으면 cp949 오류가 나므로 `PYTHONIOENCODING=utf-8`을 붙입니다. 한글이 들어간 패치는 heredoc보다 스크립트 파일로 실행하는 편이 안전합니다.
- 이 작업 PC에는 MX OPC Server · GX Works2 · 32비트 Python이 없습니다. OPC 실기 확인은 테스트 PC에서 사용자가 합니다.
- HTML 시뮬레이터 검증은 헤드리스 Edge로 합니다:
  `"C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" --headless=new --disable-gpu --virtual-time-budget=20000 --dump-dom file:///<시험용 HTML>`
  - 원본 HTML을 고치지 말고 스크래치 폴더에 복사본을 만들어 `</body>` 앞에 시험 스크립트를 넣습니다.
  - 2D(`v7.html`)는 `updatePipelineAnimation(t)`을 직접 호출해 시간을 진행하고, 3D(`3d_layout.html`)는 `window.__sim.step(dt)`를 씁니다. 3D는 `--use-angle=swiftshader --enable-unsafe-swiftshader`가 필요합니다.
  - 화면 확인은 `--screenshot`으로 PNG를 만들어 봅니다.

## 큰 파일 수정

- `v7.html`(약 4,000줄)과 `3d_layout.html`은 정확한 문자열 치환으로 고칩니다. 치환 대상이 정확히 1번 나오는지 확인하고, 아니면 멈춥니다.
- 구간(시작 ~ 끝 표시) 단위로 바꿀 때는 그 사이에 다른 함수가 없는지 먼저 확인합니다. 수정 후 함수 목록 · 요소 ID 목록을 이전 버전(`git show HEAD:v7.html`)과 대조합니다.
- 줄바꿈(CRLF/LF)은 파일의 원래 형식을 유지합니다.
