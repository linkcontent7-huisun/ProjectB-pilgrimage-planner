# 실행 환경

- OS: Windows 11 Home (10.0.26200)
- 셸: Git Bash / PowerShell
- 가상환경: `.venv` (`py -3.13 -m venv .venv`)

> **주의**: 이 PC의 Python 3.14.2는 `_ctypes` DLL이 깨져 있어(`ImportError: DLL load failed while importing _ctypes`)
> `httpx`·`openai` 계열이 동작하지 않는다. M1-2와 같이 **Python 3.13**으로 venv를 만든다.

## python --version

```
Python 3.13.14
```

## pip freeze

```
annotated-doc==0.0.5
annotated-types==0.8.0
anyio==4.15.1
attrs==26.1.0
certifi==2026.7.22
charset-normalizer==3.5.1
click==8.5.0
colorama==0.4.6
distro==1.9.0
fastapi==0.141.1
h11==0.16.0
httpcore==1.0.9
httpcore2==2.12.0
httptools==0.8.0
httpx==0.28.1
httpx2==2.12.0
idna==3.19
iniconfig==2.3.0
jiter==0.16.0
jsonpatch==1.33
jsonpointer==3.1.1
jsonschema==4.26.0
jsonschema-specifications==2025.9.1
langchain-core==1.6.2
langchain-openai==1.6.2
langchain-protocol==0.0.19
langgraph==1.2.11
langgraph-checkpoint==4.2.0
langgraph-prebuilt==1.1.0
langgraph-sdk==0.4.4
langsmith==0.12.4
openai==3.13.0
orjson==3.12.0
ormsgpack==1.12.2
packaging==26.3
pluggy==1.6.0
pydantic==2.13.5
pydantic_core==2.46.5
Pygments==2.21.0
pytest==9.1.1
pytest-asyncio==1.4.0
python-dotenv==1.2.3
PyYAML==6.0.3
referencing==0.37.0
regex==2026.9.10
requests==2.34.2
requests-toolbelt==1.0.0
rpds-py==2026.6.3
sniffio==1.3.1
sse-starlette==3.4.11
starlette==1.6.0
tenacity==9.1.4
tiktoken==0.14.0
truststore==0.10.4
typing-inspection==0.4.4
typing_extensions==4.16.0
urllib3==2.7.0
uuid_utils==0.17.1
uvicorn==0.52.4
watchfiles==1.2.0
websockets==16.1.1
xxhash==4.0.1
zstandard==0.25.0
```

## 실행 명령

```bash
py -3.13 -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
PYTHONUTF8=1 .venv/Scripts/python scripts/probe_tool_calling.py   # 도구 호출 실험
.venv/Scripts/python -m pytest -q                                   # 스키마 테스트
```

`PYTHONUTF8=1`은 Windows 콘솔(cp949)에서 한글·특수문자 출력 오류를 막기 위한 설정이다.
