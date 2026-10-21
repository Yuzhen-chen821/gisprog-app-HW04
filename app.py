"""臺北 YouBike 空站觀察：115-1 地理資訊系統運用程式的 App 範本。

執行方式：在終端機輸入 solara run app.py
"""

from pathlib import Path

from ipyleaflet import TileLayer
from leafmap.leafmap import Map as LeafmapMap
import pandas as pd
import plotly.express as px
import solara

DATA_PATH = Path(__file__).parent / "data" / "03_youbike_clean_long.csv"

# 讀檔放在元件外面：App 啟動時只讀一次，切換選項時不會重新讀檔。
# sno、act 指定為字串，避免被自動轉成整數（W3 的 read_json 陷阱，read_csv 也一樣）。
df = pd.read_csv(DATA_PATH, dtype={"sno": str, "act": str})
df = df[df["act"] == "1"]  # 只看營運中的站

時段們 = sorted(df["時段"].unique())
最新資料時間 = df["snapshot_time"].max()

# reactive：值改變時，用到它的元件會自動重新執行。
時段 = solara.reactive(時段們[0])
行政區們 = sorted(df["sarea"].dropna().unique().tolist())
行政區 = solara.reactive(行政區們[0])

級距名稱 = ["0 輛", "1–3 輛", "4–9 輛", "10 輛以上"]
級距顏色 = {
    "0 輛": "#440154",
    "1–3 輛": "#31688e",
    "4–9 輛": "#35b779",
    "10 輛以上": "#fde725",
}


def 可借車數級距(可借車數):
    """依可借車數回傳地圖與圖表使用的級距名稱。"""
    if 可借車數 < 0:
        raise ValueError("可借車數不可為負數。")
    if 可借車數 == 0:
        return "0 輛"
    if 可借車數 <= 3:
        return "1–3 輛"
    if 可借車數 <= 9:
        return "4–9 輛"
    return "10 輛以上"


def 建立站點GeoJSON(資料):
    """將站點資料轉成 GeoJSON 點圖層。"""
    features = []
    for row in 資料.to_dict("records"):
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "站名": row["sna"],
                    "可借車數": int(row["available_rent_bikes"]),
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [
                        float(row["longitude"]),
                        float(row["latitude"]),
                    ],
                },
            }
        )
    return {"type": "FeatureCollection", "features": features}


def 篩選站點資料(行政區名稱, 時段名稱):
    """依行政區與時段篩選站點，並加入可借車數級距。"""
    資料 = df.loc[
        (df["sarea"] == 行政區名稱) & (df["時段"] == 時段名稱)
    ].copy()
    資料["可借車數級距"] = 資料["available_rent_bikes"].map(可借車數級距)
    return 資料


def 建立YouBike地圖(資料):
    """建立只含目前篩選站點的 ipyleaflet 地圖。"""
    底圖 = TileLayer(
        url="https://wmts.nlsc.gov.tw/wmts/EMAP/default/EPSG:3857/{z}/{y}/{x}",
        name="臺灣通用電子地圖",
        attribution=(
            '底圖：<a href="https://maps.nlsc.gov.tw/">'
            '內政部國土測繪中心</a>'
        ),
        base=True,
    )
    地圖 = LeafmapMap(center=(25.033, 121.5654), zoom=12, basemap=底圖)
    地圖.layout.width = "100%"
    地圖.layout.height = "460px"

    GeoJSON = 建立站點GeoJSON(資料)
    if GeoJSON["features"]:
        def 站點樣式(feature):
            可借車數 = feature["properties"]["可借車數"]
            顏色 = 級距顏色[可借車數級距(可借車數)]
            return {
                "color": 顏色,
                "fillColor": 顏色,
                "fillOpacity": 0.85,
                "weight": 1,
            }

        地圖.add_geojson(
            GeoJSON,
            layer_name="YouBike 站點",
            info_mode="on_click",
            point_style={"radius": 7},
            style_callback=站點樣式,
            zoom_to_layer=True,
        )

    地圖.add_legend(title="可借車數", legend_dict=級距顏色)
    return 地圖

@solara.component
def Page():
    solara.Title("YouBike 站點可借車數")
    solara.Markdown("# 臺北 YouBike 站點可借車數分布")

    solara.Select(
        label="選擇行政區",
        value=行政區,
        values=行政區們
    )
    solara.Select(
        label="選擇時段",
        value=時段,
        values=時段們
    )

    站點資料 = solara.use_memo(
        lambda: 篩選站點資料(行政區.value, 時段.value),
        dependencies=[行政區.value, 時段.value],
    )
    地圖 = solara.use_memo(
        lambda: 建立YouBike地圖(站點資料),
        dependencies=[行政區.value, 時段.value],
    )

    級距統計 = (
        站點資料["可借車數級距"]
        .value_counts()
        .reindex(級距名稱, fill_value=0)
        .rename_axis("可借車數級距")
        .reset_index(name="站數")
    )
    圖 = px.bar(
        級距統計,
        x="可借車數級距",
        y="站數",
        color="可借車數級距",
        color_discrete_map=級距顏色,
        category_orders={"可借車數級距": 級距名稱},
        title=f"{行政區.value} {時段.value}各級距站點數",
        labels={"可借車數級距": "可借車數", "站數": "站點數"},
    )
    圖.update_layout(autosize=True, height=380)

    顯示表格 = (
        站點資料[["sna", "available_rent_bikes", "可借車數級距"]]
        .rename(
            columns={
                "sna": "站名",
                "available_rent_bikes": "可借車數",
            }
        )
        .sort_values("站名")
    )

    with solara.ColumnsResponsive(12, medium=6):
        with solara.Column(style={"min-width": "0", "max-width": "100%"}):
            solara.Markdown(f"## {行政區.value}・{時段.value}站點地圖")
        solara.display(地圖)
        with solara.Column(style={"min-width": "0", "max-width": "100%"}):
            solara.FigurePlotly(圖)
            solara.DataFrame(顯示表格)

    solara.Markdown(
        "資料來源：臺北市 YouBike 2.0 資料（臺北市資料大平臺）。"
        f"資料時間：{最新資料時間}。"
        "底圖來源：內政部國土測繪中心，臺灣通用電子地圖（WMTS）。"
    )
