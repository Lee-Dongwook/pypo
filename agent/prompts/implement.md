# 지금 할 일: 구현

계획대로 코드를 고친다.

# 계획

$plan
$feedback

# 출력 형식

바꿀 부분만 SEARCH/REPLACE 블록으로 출력한다. 파일 전체를 다시 쓰지 않는다.

- SEARCH에는 "수정할 파일"의 현재 내용을 **한 글자도 바꾸지 않고** 복사한다. 파일 안에서 딱 한 곳만 가리키도록 앞뒤 줄을 충분히 넣는다.
- REPLACE에는 그 부분을 바꾼 결과를 쓴다.
- 파일 끝에 덧붙이거나 새 파일을 만들 때는 SEARCH를 비운다.
- 한 파일에 블록을 여러 개 써도 된다. 블록 밖에는 아무것도 쓰지 않는다.

예시는 **형식만** 보여 준다. 예시의 파일 경로, 함수, 코드를 쓰지 않는다. 이슈의 완료 기준을 하나씩 모두 코드로 옮긴다.

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
<<<<<<< SEARCH
=======


def perimeter(w, h):
    return 2 * (w + h)
>>>>>>> REPLACE
=== END ===
