
import streamlit as st
import pandas as pd
import plotly.express as px
from itertools import combinations
from collections import Counter
import re

# ----------------------------------
# 기본 설정
# ----------------------------------

st.set_page_config(
    page_title="급식 규칙 찾기",
    page_icon="🍱",
    layout="wide"
)

st.title("🍱 급식 규칙 찾기")
st.write("송탄고 급식 메뉴의 연관 규칙을 분석합니다.")

DATA_URL = (
    "https://raw.githubusercontent.com/it-teacher-go/"
    "data-share-/main/songtan_meals_184.csv"
)

# ----------------------------------
# 데이터 불러오기
# ----------------------------------

@st.cache_data
def load_data():
    df = pd.read_csv(DATA_URL, encoding="utf-8-sig")

    required_columns = ["날짜", "식사", "메뉴"]

    for col in required_columns:
        if col not in df.columns:
            raise ValueError(f"CSV에 '{col}' 열이 없습니다.")

    df = df.dropna(subset=["메뉴"]).copy()

    return df


# ----------------------------------
# 메뉴 이름 정리
# ----------------------------------

def clean_menu(menu):
    menu = str(menu)

    # 괄호와 괄호 안의 내용 제거
    menu = re.sub(r"\([^)]*\)", "", menu)
    menu = re.sub(r"（[^）]*）", "", menu)

    return menu.strip()


# ----------------------------------
# 장바구니 만들기
# ----------------------------------

def make_baskets(df):

    baskets = []
    all_menus = set()

    for menu_text in df["메뉴"]:

        menu_list = str(menu_text).split("|")

        cleaned = []

        for menu in menu_list:

            menu = clean_menu(menu)

            if menu:
                cleaned.append(menu)

        # 같은 날 같은 메뉴가 중복되면 한 번만 계산
        basket = sorted(set(cleaned))

        if basket:
            baskets.append(set(basket))
            all_menus.update(basket)

    return baskets, all_menus


# ----------------------------------
# 연관 규칙 분석
# ----------------------------------

def analyze_rules(baskets):

    total_days = len(baskets)

    menu_counts = Counter()
    pair_counts = Counter()

    # 메뉴 등장 횟수 계산
    for basket in baskets:
        menu_counts.update(basket)

        # 같은 날 함께 나온 메뉴 쌍
        pairs = combinations(sorted(basket), 2)

        pair_counts.update(pairs)

    rules = []

    # 양방향 규칙 생성
    for (menu_a, menu_b), count in pair_counts.items():

        # A → B
        for condition, result in [
            (menu_a, menu_b),
            (menu_b, menu_a)
        ]:

            support = count / total_days

            confidence = count / menu_counts[condition]

            result_support = menu_counts[result] / total_days

            lift = confidence / result_support

            rules.append({
                "조건": condition,
                "결과": result,
                "동시": count,
                "지지도": support,
                "신뢰도": confidence,
                "향상도": lift
            })

    return pd.DataFrame(rules), len(pair_counts)


# ----------------------------------
# 데이터 실행
# ----------------------------------

try:
    df = load_data()

    baskets, all_menus = make_baskets(df)

    if not baskets:
        st.warning("분석할 급식 데이터가 없습니다.")
        st.stop()

    rules_df, pair_total = analyze_rules(baskets)

except Exception as e:
    st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
    st.stop()


# ----------------------------------
# 기본 통계
# ----------------------------------

st.subheader("📊 급식 데이터 요약")

st.markdown(
    f"""
    **급식 일수:** {len(baskets):,}일　|　
    **메뉴 종류 수:** {len(all_menus):,}개　|　
    **함께 나온 메뉴 쌍의 수:** {pair_total:,}쌍
    """
)

st.divider()


# ----------------------------------
# 메뉴 선택
# ----------------------------------

st.subheader("🔎 메뉴별 연관 규칙 찾기")

menu_options = ["전체 메뉴"] + sorted(all_menus)

selected_menu = st.selectbox(
    "분석할 메뉴를 선택하세요.",
    menu_options
)

# 선택한 메뉴가 조건 또는 결과에 있는 규칙만 표시
if selected_menu != "전체 메뉴":

    filtered_rules = rules_df[
        (rules_df["조건"] == selected_menu) |
        (rules_df["결과"] == selected_menu)
    ].copy()

else:

    filtered_rules = rules_df.copy()


# ----------------------------------
# 정렬 방식 선택
# ----------------------------------

sort_option = st.selectbox(
    "정렬 기준",
    ["향상도 순", "신뢰도 순", "동시 순"]
)

sort_columns = {
    "향상도 순": "향상도",
    "신뢰도 순": "신뢰도",
    "동시 순": "동시"
}

sort_column = sort_columns[sort_option]

filtered_rules = filtered_rules.sort_values(
    by=[sort_column, "신뢰도", "동시"],
    ascending=[False, False, False]
).reset_index(drop=True)


# ----------------------------------
# 연관 규칙 표
# ----------------------------------

st.subheader("📋 메뉴 연관 규칙")

if len(filtered_rules) > 0:

    st.dataframe(
        filtered_rules[
            [
                "조건",
                "결과",
                "동시",
                "지지도",
                "신뢰도",
                "향상도"
            ]
        ].style.format({
            "지지도": "{:.2%}",
            "신뢰도": "{:.2%}",
            "향상도": "{:.3f}"
        }),
        use_container_width=True,
        hide_index=True
    )

else:

    st.info("선택한 메뉴와 관련된 규칙이 없습니다.")


# ----------------------------------
# 향상도 상위 10개 그래프
# ----------------------------------

st.divider()

st.subheader("📈 향상도 상위 10개 규칙")

if len(filtered_rules) > 0:

    # 필터링된 규칙 중 향상도가 높은 10개
    top10 = filtered_rules.sort_values(
        by=["향상도", "신뢰도", "동시"],
        ascending=[False, False, False]
    ).head(10).copy()

    # 그래프 표시용 이름
    top10["규칙"] = (
        top10["조건"] + " → " + top10["결과"]
    )

    fig = px.bar(
        top10.sort_values("향상도", ascending=True),
        x="향상도",
        y="규칙",
        orientation="h",
        text="향상도",
        hover_data={
            "조건": True,
            "결과": True,
            "동시": True,
            "지지도": ":.2%",
            "신뢰도": ":.2%",
            "향상도": ":.3f",
            "규칙": False
        },
        labels={
            "향상도": "향상도 (Lift)",
            "규칙": "연관 규칙"
        },
        title="향상도가 높은 메뉴 연관 규칙 TOP 10"
    )

    fig.update_traces(
        texttemplate="%{text:.3f}",
        textposition="outside"
    )

    fig.update_layout(
        height=500,
        xaxis_title="향상도",
        yaxis_title="메뉴 규칙",
        margin=dict(l=20, r=50, t=60, b=30)
    )

    st.plotly_chart(fig, use_container_width=True)

else:

    st.info("그래프로 표시할 연관 규칙이 없습니다.")


# ----------------------------------
# 분석 지표 설명
# ----------------------------------

st.divider()

st.subheader("📖 연관 규칙 분석 용어")

st.markdown(
    """
    - **조건:** 먼저 등장하는 메뉴
    - **결과:** 조건 메뉴와 함께 등장하는 메뉴
    - **동시:** 두 메뉴가 같은 날 함께 나온 횟수
    - **지지도:** 전체 급식 중 두 메뉴가 함께 나온 비율
    - **신뢰도:** 조건 메뉴가 나왔을 때 결과 메뉴도 나온 비율
    - **향상도:** 두 메뉴의 연관성이 우연히 함께 나오는 경우보다 얼마나 높은지 나타내는 값

    **향상도 해석**

    - 향상도 > 1 : 양의 연관성이 있음
    - 향상도 = 1 : 독립적인 관계
    - 향상도 < 1 : 음의 연관성이 있음
    """
)

st.caption("송탄고 중식 급식 데이터 연관 규칙 분석 앱")
