# 실수와 해결

pypo가 실패했다가 고친 작업에서 배운 것입니다. 회고 단계에서 코드가 덧붙이고, PR 리뷰로 검수합니다.

- #21 상황: `tests/test_card_calculator.py` 파일에서 `Card`와 `Tier` 클래스가 재정의되어 오류 발생. / 원인: 각각의 테스트 함수 내에서 `Card`와 `Tier`를 다시 정의했기 때문에. / 해결: `Card`와 `Tier`는 이미 `src/app/card/schemas.py`에서 정의되어 있으므로, 해당 파일에서 import하여 사용하면 됩니다.
- #22 상황: 이슈 #22의 요구사항을 충족시키기 위해 테스트를 추가하려고 했으나, 해당 테스트가 이미 존재하지 않았습니다. / 원인: `tests/test_card_api.py` 파일에서 `test_optimize_without_cards_is_rejected`와 `test_tier_analysis_without_cards_is_rejected`라는 이름의 테스트 함수가 정의되어 있지 않았습니다. / 해결: 이 두 테스트 함수를 추가하여 요구사항을 충족시켰으며, 해당 코드 변경이 통과되었습니다.
