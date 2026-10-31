# 지금 할 일: 구현

이슈의 완료 기준을 하나씩 모두 코드로 옮긴다. "통과해야 할 테스트"에 이름이 있으면 그 이름 그대로 테스트를 만든다.

$feedback

# 출력 형식

**설명을 쓰지 않는다.** 첫 줄부터 바로 `=== FILE: <경로> ===`로 시작한다. 파일마다 블록 하나를 쓰고 `=== END ===`로 닫는다.

블록 안에는 아래 방식을 쓴다. 한 블록에 섞어 써도 된다.

1. **덧붙이기·새 파일:** 파일 끝에 붙일 코드만 쓴다. 기존 코드를 다시 쓰지 않는다. 새로 필요한 import는 코드 맨 위에 쓰면 pypo가 import 자리로 옮긴다.
2. **기존 코드 바꾸기:** SEARCH/REPLACE를 쓴다. SEARCH에는 현재 내용을 한 글자도 바꾸지 않고 복사하고, 파일 안에서 딱 한 곳만 가리키도록 앞뒤 줄을 충분히 넣는다.
3. **함수·클래스를 다른 파일로 옮기기:** 원래 파일 블록에 `MOVE 이름 TO <새 경로>` 한 줄만 쓴다. 옮길 코드를 다시 쓰지 않고, 새 파일 블록도 쓰지 않는다. pypo가 정의를 새 파일 끝으로 옮기고, 원래 파일에 새 위치에서 가져오는 import를 넣는다. 다른 파일이 그 이름을 원래 파일에서 import하고 있으면, 그 파일 블록에서 import를 SEARCH/REPLACE로 고친다.
4. **함수·클래스 통째로 지우기:** `DELETE 이름` 한 줄만 쓴다. 지울 코드를 베끼지 않는다. 다른 파일로 옮기는 거라면 DELETE가 아니라 MOVE를 쓴다.
5. **함수·클래스 이름 바꾸기:** 정의가 있는 파일 블록에 `RENAME 이름 TO 새이름` 한 줄만 쓴다. pypo가 그 파일과 이슈에 적힌 파일에서 쓰는 곳을 모두 바꾼다.

어떤 경우에도 파일 전체를 다시 쓰지 않는다.

쓰지 않게 된 import는 pypo가 지우고, `src/`에 정의가 하나뿐인 이름은 import를 빠뜨려도 pypo가 넣는다.

예시는 **형식만** 보여 준다. 예시의 파일 경로, 함수, 코드를 쓰지 않는다.

덧붙이기 예시:

=== FILE: lib/test_shapes.py ===
from lib.shapes import perimeter


def test_perimeter_of_square():
    assert perimeter(2, 2) == 8
=== END ===

옮기기 예시 (`Box`를 `lib/shapes.py`에서 `lib/models.py`로 옮기고, `lib/draw.py`의 import를 고친다):

=== FILE: lib/shapes.py ===
MOVE Box TO lib/models.py
=== END ===
=== FILE: lib/draw.py ===
<<<<<<< SEARCH
from .shapes import Box, area
=======
from .models import Box
from .shapes import area
>>>>>>> REPLACE
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
