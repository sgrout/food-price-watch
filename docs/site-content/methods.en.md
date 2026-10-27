# How the forecasts work

## What this is

Forecasts of staple food prices per market, for the next months, with an honest range and a
published track record. The prices come from the World Food Programme (WFP) via the Humanitarian Data Exchange
(HDX). This is a free, non-commercial tool for organisations without their own data team. **It is not an official
assessment**: for those, see [WFP HungerMap](https://hungermap.wfp.org) and [FEWS NET](https://fews.net).

## Which data a forecast uses

WFP publishes each month's prices one to two and a half months later. A forecast made
in a month therefore uses only the prices published by then: a forecast made in October uses prices up to August. The
first two months shown (the last month and the current month) are estimates of prices not yet published; the next
three are forecasts. In some markets WFP publishes faster: the last month's price is then already in the history,
next to its estimate, but this forecast does not use it yet (it will next month).

## How a forecast is made

One model learns from all markets at once. For each food and market it looks at how far
the price is from the usual level for that time of year, how the price moved over the last months, and how the same
food moved in the country's other markets. It gives a range of likely prices, not a single number. The range is then
corrected with the model's own past mistakes, using only mistakes that were already known at the time.

## How to read the range

The 80 % range means: if the track record holds, the real price will fall inside it about
8 times in 10. The track record page shows how often that really happened.

How to use it: the most likely value shows the direction (for example a fall after the harvest); the upper end
shows how high the price could plausibly go, for example as a margin when planning a budget. Within a country, a
wider range means less certainty in that market.

## Why the ranges are wide

The ranges are wide because food prices really move this much, and we would rather show that than look more
precise than we are. A narrower range would look better but be wrong more often. Three things make them wider:

- **Prices move a lot.** Around the harvest and the lean season, staple prices can rise or fall sharply within a
  few months, and the timing differs from year to year.
- **The newest price is already old.** WFP publishes prices about two months late, so "next month" is about three
  months after the last known price.
- **Some markets report irregularly.** If a market has not reported a price for a while, the forecast starts from
  an older price and its range is wider still; the text then says so.

In tests on 2023 onwards, the typical miss (half of the errors were smaller) was about 5 % for the month just past,
about 10 % for next month and about 15 % three months ahead, for single foods and for the basket alike.

## What a spike is

A price well above the usual level for that time of year: at least one standard deviation above
a seasonal trend fitted on the last ten years. The levels are normal, stress, alert and crisis, following WFP's Alert
for Price Spikes (ALPS). Our version differs from WFP's in three ways: it uses relative (log) prices, a ten-year
window, and only data that was available at the time (WFP fits the whole series). Past spikes shown here will
therefore not always match WFP's charts.

## Food basket

For some markets the site also shows the cost of a simple staple basket for one person for one
month, based on a typical WFP food ration (12 kg cereal, 1.8 kg pulses, 0.75 L oil), with only the foods that WFP
monitors long enough in that country. It is made by Staple Signals and is **not an official minimum expenditure
basket**. Its range combines the forecasts of the foods in it, taking into account how their past errors moved
together, so it is wider when the foods tend to rise and fall together.

## Distance from the national price

For each food, the page compares the market's price with the median price of the same food in the country's other
markets that month (at least five markets), and with the market's own usual distance over the three years before.
Remote markets are often dearer all the time, so what matters is a distance that grows. In blockaded or cut-off
areas, prices can separate from the rest of the country, and a national average hides exactly those places. A
market is marked when its price is at least 25 % above the national median and clearly above its usual distance.
This is a description of the data, not a forecast or a proven warning: a data error can look the same.

## Markets that stopped reporting

A market that has published no price for any food for two months or more is shown as such, with its last prices,
instead of disappearing. Months are counted from the latest month most markets in the country reported, so WFP's
normal publication delay does not count as silence. In conflict areas, missing data can be an early sign of
trouble, but it can also have other causes, such as a pause in monitoring or a change in the list of markets WFP
follows.

## Data checks

A value that jumps and fully reverses the next month is marked as a data error and not used, once the
next month is published. A big jump in the latest month is marked as not yet confirmed. Foods that WFP renamed are
linked only when the price level matches. Nothing is silently corrected.

## Known limits

- Warnings of *new* spikes have no proven skill yet: the spike chance is shown for next month only, because further
  ahead it scored worse than simply using how often spikes happen.
- The wider (95 %) ranges are loose, especially after a sudden jump; rely on the 80 % range.
- WFP may revise old months; that history cannot be reconstructed, so the past test uses today's values.
- Some markets report identical prices for many months; they may be real or carried forward, and such series look
  calmer than they are.
- Markets in conflict areas report less often, especially during crises. Markets that published a price in fewer
  than 9 of the last 12 months are marked.
- Prices are in local currency, not adjusted for inflation.

## Source and license

World Food Programme, food prices on HDX, CC BY-IGO.
