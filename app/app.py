import streamlit as st

st.set_page_config(page_title="food-price-watch", page_icon="🌾", layout="wide")  # must be the first st call

import views  # noqa: E402
from strings import ATTRIBUTION  # noqa: E402

page = st.navigation([
    st.Page(views.market_page, title="Market and food", icon="📈", url_path="market", default=True),
    st.Page(views.track_record_page, title="Track record", icon="🎯", url_path="track-record"),
    st.Page(views.methods_page, title="Methods", icon="📖", url_path="methods"),
])
page.run()
st.divider()
st.caption(ATTRIBUTION)
