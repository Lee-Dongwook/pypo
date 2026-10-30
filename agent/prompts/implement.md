# 지금 할 일: 구현

이슈의 완료 기준을 하나씩 모두 코드로 옮긴다. "통과해야 할 테스트"에 이름이 있으면 그 이름 그대로 테스트를 만든다.

$feedback

# 출력 형식

**설명을 쓰지 않는다.** 첫 줄부터 바로 `=== FILE: <경로> ===`로 시작한다. 파일마다 블록 하나를 쓰고 `=== END ===`로 닫는다.

블록 안에는 두 가지 중 하나를 쓴다.

1. **덧붙이기·새 파일:** 파일 끝에 붙일 코드만 쓴다. 기존 코드를 다시 쓰지 않는다. 새로 필요한 import는 코드 맨 위에 쓰면 pypo가 import 자리로 옮긴다.
2. **기존 코드 바꾸기:** SEARCH/REPLACE를 쓴다. SEARCH에는 현재 내용을 한 글자도 바꾸지 않고 복사하고, 파일 안에서 딱 한 곳만 가리키도록 앞뒤 줄을 충분히 넣는다.

예시는 **형식만** 보여 준다. 예시의 파일 경로, 함수, 코드를 쓰지 않는다.

덧붙이기 예시:

=== FILE: lib/test_shapes.py ===
from lib.shapes import perimeter


def test_perimeter_of_square():
    assert perimeter(2, 2) == 8
=== END ===

바꾸기 예시:

=== FILE: lib/shapes.py ===
<<<<<<< SEARCH
def area(w, h):
    return w * h
=======
def area(w, h):
    if w < 0 or h < 0:
        raise ValueError("negative size")
    return w * h
>>>>>>> REPLACE
=== END ===
