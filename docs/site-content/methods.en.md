# How the forecasts work

**What this is.** Forecasts of staple food prices per market, for the next months, with an honest range and a
published track record. The prices come from the World Food Programme (WFP) via the Humanitarian Data Exchange
(HDX). This is a free, non-commercial tool for organisations without their own data team. **It is not an official
assessment**: for those, see [WFP HungerMap](https://hungermap.wfp.org) and [FEWS NET](https://fews.net).

**Which data a forecast uses.** WFP publishes each month's prices one to two and a half months later. A forecast made
in a month therefore uses only the prices published by then: a forecast made in October uses prices up to August. The
first two months shown (the last month and the current month) are estimates of prices not yet published; the next
three are forecasts.

**How a forecast is made.** One model learns from all markets at once. For each food and market it looks at how far
the price is from the usual level for that time of year, how the price moved over the last months, and how the same
food moved in the country's other markets. It gives a range of likely prices, not a single number. The range is then
corrected with the model's own past mistakes, using only mistakes that were already known at the time.

**How to read the range.** The 80 % range means: if the track record holds, the real price will fall inside it about
8 times in 10. The track record page shows how often that really happened.

**What a spike is.** A price well above the usual level for that time of year: at least one standard deviation above
a seasonal trend fitted on the last ten years. The levels are normal, stress, alert and crisis, following WFP's Alert
for Price Spikes (ALPS). Our version differs from WFP's in three ways: it uses relative (log) prices, a ten-year
window, and only data that was available at the time (WFP fits the whole series). Past spikes shown here will
therefore not always match WFP's charts.

**Data checks.** A value that jumps and fully reverses the next month is marked as a data error and not used, once the
next month is published. A big jump in the latest month is marked as not yet confirmed. Foods that WFP renamed are
linked only when the price level matches. Nothing is silently corrected.

**Known limits.**
- Warnings of *new* spikes have no proven skill yet: the spike chance is shown for next month only, because further
  ahead it scored worse than simply using how often spikes happen.
- The wider (95 %) ranges are loose, especially after a sudden jump; rely on the 80 % range.
- WFP may revise old months; that history cannot be reconstructed, so the past test uses today's values.
- Some markets report identical prices for many months; they may be real or carried forward, and such series look
  calmer than they are.
- Markets in conflict areas report less often, especially during crises. Markets that published a price in fewer
  than 9 of the last 12 months are marked.
- Prices are in local currency, not adjusted for inflation.

**Source and license.** World Food Programme, food prices on HDX, CC BY-IGO.
