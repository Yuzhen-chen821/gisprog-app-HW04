"""臺北 YouBike 空站觀察：115-1 地理資訊系統運用程式的 App 範本。

執行方式：在終端機輸入 solara run app.py
"""

from pathlib import Path

import pandas as pd
import plotly.express as px
import solara

DATA_PATH = Path(__file__).parent / "data" / "03_youbike_clean_long.csv"

# 讀檔放在元件外面：App 啟動時只讀一次，切換選項時不會重新讀檔。
# sno、act 指定為字串，避免被自動轉成整數（W3 的 read_json 陷阱，read_csv 也一樣）。
df = pd.read_csv(DATA_PATH, dtype={"sno": str, "act": str})
df = df[df["act"] == "1"]  # 只看營運中的站

時段們 = sorted(df["時段"].unique())

# reactive：值改變時，用到它的元件會自動重新執行。
門檻 = solara.reactive(0)
時段 = solara.reactive(時段們[0])
行政區們 = sorted(df["sarea"].dropna().unique().tolist())
行政區 = solara.reactive(行政區們[0])

def 各區空站比例(資料, 門檻值):
    """計算各區的站數、空站數與空站比例（可借車 <= 門檻值 算空站）。"""
    資料 = 資料.assign(空站=資料["available_rent_bikes"] <= 門檻值)
    表 = 資料.groupby("sarea").agg(站數=("sno", "size"), 空站數=("空站", "sum"))
    表["空站比例"] = (表["空站數"] / 表["站數"]).round(3)
    return 表.sort_values("空站比例", ascending=False).reset_index()
def 行政區各時段空站比例(資料, 行政區名稱, 門檻值):
    區資料 = 資料[資料["sarea"] == 行政區名稱].copy()

    區資料["空站"] = (
        區資料["available_rent_bikes"] <= 門檻值
    )
    
    表 = 區資料.groupby("時段").agg(
        站數=("sno", "size"),
        空站數=("空站", "sum")
    ).reset_index()

    表["空站比例"] = (
        表["空站數"] / 表["站數"]
    ).round(3)

    return 表

@solara.component
def Page():
    solara.Title("YouBike 空站觀察")
    solara.Markdown("# 臺北 YouBike 行政區各時段空站比例")

    solara.Select(
        label="選擇行政區",
        value=行政區,
        values=行政區們
    )

    with solara.Column(style={"max-width": "480px"}):
        solara.SliderInt(
            "空站門檻：可借車 ≤",
            value=門檻,
            min=0,
            max=5
        )

    表 = 行政區各時段空站比例(
        df,
        行政區.value,
        門檻.value
    )

    圖 = px.bar(
        表,
        x="時段",
        y="空站比例",
        title=f"{行政區.value}各時段空站比例",
        labels={
            "時段": "資料時間",
            "空站比例": "空站比例"
        }
    )

    圖.update_layout(
        yaxis_tickformat=".0%",
        height=450
    )

    solara.FigurePlotly(圖)
    solara.DataFrame(表)

    solara.Markdown(
        "資料來源：臺北市 YouBike 2.0 即時資料（臺北市資料大平臺）。"
        "資料日期：2026/09/30。"
    )
