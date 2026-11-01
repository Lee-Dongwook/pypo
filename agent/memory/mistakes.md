# 실수와 해결

pypo가 실패했다가 고친 작업에서 배운 것입니다. 회고 단계에서 코드가 덧붙이고, PR 리뷰로 검수합니다.

- #21 상황: `tests/test_card_calculator.py` 파일에서 `Card`와 `Tier` 클래스가 재정의되어 오류 발생. / 원인: 각각의 테스트 함수 내에서 `Card`와 `Tier`를 다시 정의했기 때문에. / 해결: `Card`와 `Tier`는 이미 `src/app/card/schemas.py`에서 정의되어 있으므로, 해당 파일에서 import하여 사용하면 됩니다.
