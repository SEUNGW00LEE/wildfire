## GLPK 설치 및 설정
이 프로젝트는 기본적으로 GLPK 솔버를 사용합니다. GLPK를 설치하고, 필요 시 `config.json` 파일의 `"executable_path"`를 설정하세요.

### 리눅스
1. `sudo apt-get install glpk-utils` 실행
2. 기본 경로: `"/usr/bin/glpsol"`

### 윈도우
1. [GLPK for Windows](https://sourceforge.net/projects/winglpk/)에서 다운로드
2. 설치 후 경로 설정: `"executable_path": "C:/glpk-4.65/w64/glpsol.exe"`

### 맥OS
1. `brew install glpk` 실행
2. 기본 경로: `"/usr/local/bin/glpsol"`

**참고**: GLPK가 설치되어 있으면 코드가 자동으로 경로를 탐지합니다. 탐지가 실패할 경우, 위 경로를 `config.json`에 수동으로 설정하세요.