# 로컬 번역기 백엔드와 플랫폼 어댑터 1차 설계

## 배경

BRIDGE는 선택한 창을 캡처하고, OCR로 문자를 읽고, 번역 결과를 화면 오버레이에 표시하는 Windows 데스크톱 앱이다. 현재 번역 기능은 Papago API에 직접 연결되어 있다. 이 구조는 네트워크 의존성이 있고, Papago API 상태나 인증 설정에 따라 실시간 흐름이 쉽게 끊길 수 있다.

앞으로는 Papago뿐 아니라 로컬 번역 모델, 테스트용 번역기, 다른 번역 엔진을 붙일 수 있어야 한다. 또한 화면 캡처와 오버레이는 운영체제별 구현 차이가 크므로, 장기적으로는 플랫폼별 구현을 공통 인터페이스 뒤에 숨겨야 한다.

1차 목표는 실제 로컬 모델이나 macOS/Linux 캡처 구현을 바로 확정하는 것이 아니다. 번역 기능과 플랫폼 의존 기능을 교체 가능한 구조로 만드는 것이다.

## 우선순위

사용자 우선순위는 다음과 같다.

1. 실시간 속도
2. 완전 오프라인 동작
3. 번역 품질
4. 쉬운 설치

따라서 기본 방향은 큰 LLM을 기본 번역기로 쓰는 것이 아니라, 빠른 번역 전용 모델을 나중에 붙일 수 있는 구조를 먼저 만드는 것이다.

## 1차 범위

1차 구현 범위는 다음으로 제한한다.

- 번역기 인터페이스 추가
- Papago 번역기를 인터페이스 뒤로 이동
- 테스트 번역기 추가
- 설정값으로 번역 방식 선택
- 번역 방식별 캐시 파일 분리
- `pipeline.py`가 특정 번역기 구현을 직접 알지 않도록 변경
- 화면 캡처와 오버레이를 플랫폼 어댑터 뒤로 숨길 수 있는 인터페이스 정의
- 기존 Windows 캡처와 오버레이 구현을 1차 플랫폼 어댑터로 유지

1차 범위에서 실제 CTranslate2, Argos Translate, NLLB, Ollama 같은 모델 런타임은 붙이지 않는다. macOS, Linux, iOS, Android 캡처 구현도 만들지 않는다. 실제 모델 연결과 추가 플랫폼 지원은 인터페이스가 안정된 뒤 후속 범위에서 진행한다.

## 한글 기능 단위

사용자에게 보이는 설명과 설계 문서는 한글 기능 단위를 기준으로 한다.

- 화면 캡처: 선택한 창의 화면을 이미지로 가져오는 기능
- 문자 인식: 캡처 이미지에서 글자를 읽는 기능
- 번역기: 인식된 문장을 번역하는 기능
- 번역기 선택: Papago, 로컬 번역기, 테스트 번역기 중 하나를 고르는 기능
- 번역 캐시: 이미 번역한 문장을 저장해서 다시 번역하지 않는 기능
- 오버레이 표시: 번역 결과를 화면 위에 띄우는 기능
- 플랫폼 어댑터: Windows, macOS, Linux처럼 운영체제별로 다른 기능을 공통 인터페이스로 감싸는 기능
- 실시간 처리: 캡처, 문자 인식, 번역, 표시를 반복 실행하는 흐름

코드 식별자는 기존 Python 관례에 맞춰 영어를 사용한다. 예를 들어 UI와 문서에서는 "테스트 번역기"라고 부르고, 코드에서는 `DummyTranslator` 또는 `LocalDummyTranslator`처럼 표현한다.

## 아키텍처

현재 구조는 `TranslationPipeline`이 `TranslatorPapago`를 직접 생성한다.

```text
TranslationPipeline
  -> TranslatorPapago
  -> SaveCsv
  -> Overlay
```

1차 설계 후 구조는 다음과 같다.

```text
TranslationPipeline
  -> create_translator(config)
       -> PapagoTranslator
       -> LocalDummyTranslator
       -> future LocalModelTranslator
  -> SaveCsv
  -> Overlay
```

`pipeline.py`는 번역기가 Papago인지 로컬 모델인지 알지 않는다. 파이프라인은 공통 번역기 인터페이스만 사용한다.

화면 캡처와 오버레이도 같은 방향으로 분리한다. 현재 구조에서는 `pipeline.py`가 `Capture`를 직접 만들고, `main.py`가 `Overlay`를 직접 만든다. 1차 설계 후에는 플랫폼 팩토리가 현재 운영체제에 맞는 구현을 생성한다.

```text
main.py
  -> create_overlay_backend(config)
       -> WindowsOverlayBackend

TranslationPipeline
  -> create_capture_backend(config)
       -> WindowsCaptureBackend
  -> OCR
  -> Translator
  -> TranslationCache
```

이 구조에서는 Windows 전용 API인 `win32gui`, `win32ui`, `win32api`가 Windows 어댑터 내부에만 존재한다. 공통 파이프라인은 운영체제 핸들, 창 핸들, Win32 스타일 값을 알지 않는다.

## 플랫폼 어댑터

플랫폼 어댑터는 화면 캡처와 오버레이를 운영체제별 구현으로 분리하기 위한 경계다. 1차 구현에서는 Windows 구현만 제공하되, 공통 인터페이스는 다른 운영체제를 추가할 수 있도록 정의한다.

예상 구조는 다음과 같다.

```text
platforms/
  base.py
  factory.py
  windows/
    capture.py
    overlay.py
```

후속 플랫폼을 추가할 때는 다음 파일이 추가될 수 있다.

```text
platforms/
  macos/
    capture.py
    overlay.py
  linux/
    capture.py
    overlay.py
```

iOS와 Android는 현재 Python 데스크톱 앱 범위를 벗어난다. 모바일 지원이 필요해지면 별도 앱 구조와 OS 권한 모델을 전제로 다시 설계한다.

## 플랫폼 인터페이스

화면 캡처 어댑터는 다음 책임을 가진다.

- 캡처 가능한 창 목록 조회
- 사용자가 선택한 창 식별
- 선택한 창의 현재 화면 프레임 캡처
- 캡처한 프레임의 화면상 기준 좌표 제공

오버레이 어댑터는 다음 책임을 가진다.

- 오버레이 창 시작
- 이전 번역 라벨 제거
- 지정 좌표에 번역문 표시
- 오버레이 종료

공통 데이터는 운영체제 내부 객체를 포함하지 않는다. 예를 들어 Windows의 `hwnd`는 `WindowsCaptureBackend` 내부에만 있어야 하며, `pipeline.py`나 OCR/번역 계층으로 전달하지 않는다.

```text
WindowInfo
  id
  title

CapturedFrame
  image
  screen_x
  screen_y
  width
  height

OverlayText
  text
  x
  y
  width
  height
  font_size
```

## 적용 디자인 패턴

플랫폼 어댑터 분리는 GoF 기준으로 Adapter 패턴이 핵심이다.

```text
Client
  main.py, pipeline.py

Target
  CaptureBackend, OverlayBackend

Adapter
  WindowsCaptureBackend, WindowsOverlayBackend

Adaptee
  win32gui, win32ui, win32api, tkinter
```

운영체제에 맞는 구현을 생성할 때는 Factory Method 또는 Abstract Factory 성격의 팩토리를 사용한다.

```text
create_capture_backend(config)
create_overlay_backend(config)
```

번역기 선택 구조는 Strategy 패턴에 가깝다. `PapagoTranslator`, `LocalDummyTranslator`, 후속 `LocalModelTranslator`는 같은 번역 인터페이스를 구현하고 설정값에 따라 교체된다.

```text
플랫폼 캡처/오버레이 분리
  Adapter + Factory

번역기 교체 구조
  Strategy + Factory
```

## 번역기 인터페이스

모든 번역기는 같은 메서드를 제공한다.

```python
translate(text: str, source_lang: str, target_lang: str) -> TranslationResult
```

`TranslationResult`는 다음 정보를 가진다.

- `text`: 번역된 문장
- `success`: 성공 여부
- `error`: 실패 이유. 성공 시 비어 있음
- `backend`: 사용된 번역 방식

이 구조를 쓰면 번역 실패를 단순히 `None`으로 처리하지 않고, 실패 이유를 로그나 UI에 연결할 수 있다.

## 번역 방식

1차 구현에서 지원할 번역 방식은 다음과 같다.

- `local_dummy`: 테스트 번역기. 실제 번역 대신 원문 앞에 `[테스트 번역]`을 붙인다.
- `papago`: 기존 Papago API 번역기.
- `disabled`: 번역 비활성화. 원문을 그대로 반환하거나 표시하지 않는 모드로 사용한다.

`local_model`은 설정값 후보로 남길 수 있지만, 1차 구현에서 선택 가능한 완성 기능으로 노출하지 않는다. 실제 로컬 모델이 연결되기 전까지는 사용자가 혼동할 수 있기 때문이다.

## 설정

`config.py`의 JSON 설정 구조를 확장한다.

```json
{
    "translation_backend": "local_dummy",
    "translate_source_lang": "en",
    "translate_target_lang": "ko",
    "local_model_path": "",
    "papago_enabled": false
}
```

설정 의미는 다음과 같다.

- `translation_backend`: 사용할 번역 방식
- `translate_source_lang`: 원문 언어
- `translate_target_lang`: 번역 언어
- `local_model_path`: 나중에 로컬 모델 경로를 저장할 위치
- `papago_enabled`: Papago API 사용 여부

초기 기본값은 `local_dummy`로 둔다. 이렇게 하면 API 키나 모델 파일 없이도 캡처, OCR, 캐시, 오버레이 흐름을 검증할 수 있다.

## 캐시

현재 캐시는 창 이름 기준 CSV 파일에 원문과 번역문을 저장한다. 번역 백엔드가 여러 개가 되면 같은 원문이라도 결과가 달라질 수 있으므로 캐시를 분리해야 한다.

1차 구현에서는 기존 CSV 구조를 크게 바꾸지 않고 파일명만 분리한다.

```text
CSV/{창이름}.{번역방식}.{원문언어}-{번역언어}.csv
```

예시는 다음과 같다.

```text
CSV/Chrome.local_dummy.en-ko.csv
CSV/Chrome.papago.en-ko.csv
```

이 방식은 기존 캐시 파일을 삭제하거나 변환하지 않아도 되고, 번역 방식 변경 시 잘못된 캐시를 재사용하지 않는다.

## 실시간 처리

1차 구현에서는 현재 동기 처리 흐름을 유지한다.

```text
화면 캡처
-> 문자 인식
-> 문장 단위 정리
-> 캐시 확인
-> 번역기.translate()
-> 캐시 저장
-> 오버레이 표시
```

실제 로컬 모델이 느린 것으로 확인되면 2차 또는 3차에서 번역 큐를 도입한다. 1차에서 큐를 먼저 넣으면 변경 범위가 커지고, 번역기 인터페이스 검증이 흐려진다.

## 오류 처리

번역 실패 시 앱 전체를 종료하지 않는다.

- Papago 인증 실패: 오류를 로그에 남기고 원문을 반환한다.
- Papago 네트워크 실패: 오류를 로그에 남기고 원문을 반환한다.
- 알 수 없는 번역 방식: 테스트 번역기로 대체하지 않고 명확한 오류를 낸다.
- 번역 결과가 비어 있음: 원문을 반환하거나 해당 문장을 표시하지 않는다.

기본 동작은 "앱은 계속 실행, 번역 실패는 명확히 기록"이다. 실시간 오버레이 앱에서는 번역 하나가 실패해도 캡처와 OCR 루프가 유지되는 편이 낫다.

## 테스트 기준

1차 구현은 다음을 만족해야 한다.

- 테스트 번역기를 선택하면 번역 결과에 `[테스트 번역]`이 붙는다.
- Papago 번역기를 선택하면 기존 Papago 요청 코드가 인터페이스 뒤에서 실행된다.
- `pipeline.py`가 `PapagoTranslator` 같은 구체 클래스를 직접 import하지 않는다.
- `pipeline.py`가 Win32 캡처 구현을 직접 import하지 않는다.
- `main.py`가 Win32 오버레이 구현을 직접 import하지 않는다.
- 번역 방식, 원문 언어, 번역 언어가 캐시 파일명에 반영된다.
- 알 수 없는 번역 방식은 명확한 예외나 오류 결과로 처리된다.
- API 키나 로컬 모델 없이도 `local_dummy` 모드로 파이프라인을 검증할 수 있다.
- 지원하지 않는 운영체제에서는 명확한 `PlatformNotSupported` 오류가 발생한다.

## 후속 단계

2차에서는 실제 로컬 번역기 후보를 붙인다. 우선 후보는 저사양 CPU와 실시간성을 고려해 CTranslate2와 OPUS-MT 계열 모델이다. Argos Translate는 설치가 쉬운 fallback 후보로 검토한다.

3차에서는 실제 모델 성능을 보고 번역 큐를 도입한다. 큐가 들어가면 오래된 OCR 결과를 버리고 최신 문장을 우선 번역해 화면 멈춤을 줄인다.

플랫폼 확장은 번역기 안정화 이후 별도 단계로 진행한다. macOS는 ScreenCaptureKit, Linux는 xdg-desktop-portal과 PipeWire, Windows는 Windows Graphics Capture 또는 기존 Win32 캡처 구현을 비교 검토한다.
