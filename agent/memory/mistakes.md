# 실수와 해결

pypo가 실패했다가 고친 작업에서 배운 것입니다. 회고 단계에서 코드가 덧붙이고, PR 리뷰로 검수합니다.

- #3 상황: `PurchaseEvaluation` 클래스가 재정의되어 있었습니다. / 원인: `calculator.py` 파일에서 이미 `PurchaseEvaluation` 클래스가 정의되어 있었고, 다시 정의하려고 했기 때문입니다. / 해결: `calculator.py` 파일에서 `PurchaseEvaluation` 클래스의 재정의를 제거하고, 필요한 부분만 가져와서 사용하도록 수정하였습니다.
