# Where the bands came from

For years, I thought it was completely normal to know where every band came from. Radio DJs had a lot to do with it. Instead of repeating the name of a band, they would say things like "the Liverpool quartet", "the boys from Manchester". Music magazines and reviews did the same. I grew used to hearing geography woven into music talk, so I absorbed it without noticing.

It also made me dream about places that, as a Latin American kid, I was fairly sure I would never visit.

Later, after I emigrated and began meeting people from the UK, they would tell me where they were from and a band would often appear in my head. Someone would say, "Newcastle," and my mind would answer The Animals. Sometimes I said it out loud. It took me a while to realize that this was a particular trait, and not an entirely normal way to respond when meeting someone.

I tend to save it for the smaller places. I would not comment on Liverpool, London or Manchester, where the associations are too obvious. Manchester is a special case anyway. To me, it may be the ultimate city of late-80s cultural impact, because of Joy Division and New Order, The Smiths, and The Stone Roses, Happy Mondays and the rest of Madchester.

There were other cities in my musical imagination. I knew that The B-52's and R.E.M. came from the same Athens, Georgia. And of course Seattle, with a scene that swallowed an entire generation. So much was written about how one place could produce so many important bands. Was it the rain? The kids stuck indoors or in bars? I have no idea whether that explanation stood on solid ground, but I loved it. All these places were remote and expensive to reach. I was convinced I would know them only through records, radio shows and magazine articles.

One evening in late September 2025, I was watching the recording of that year's Pulp –Sheffield!– show in Glastonbury, and I began wondering how many bands I could name from each British city. The answer was quite a lot. I made a rough list from memory that eventually became the starting point for this project.

The list led to a question: Which British music city punches furthest above its weight?
(Are some of these cities more impactful to the spread of British music than others? Do larger cities have more impact?)

London should be the obvious winner. It is one of Europe's largest cities and one of the most influential cities in the world. With that many people in one place, musicians have a better chance of finding like-minded collaborators, venues, audiences and an industry willing to pay attention. Liverpool has The Beatles, of course, but what happens after The Beatles? Does the city's musical importance survive once its biggest band is taken away?

The largest act may be the wrong thing to look for. I was more interested in which cities had depth: several bands, from different periods, with audiences far beyond the places where they began. Could I measure that without relying entirely on my own taste and the catalogue of hometowns I had carried around since childhood?

That sounded like an interesting data problem.

"Which British music city punches furthest above its weight?" contains a handful of smaller questions: What counts as a city? Which bands count as belonging to it? How should popularity be measured? And what, exactly, does "above its weight" mean?

## Define a city

City boundaries are a nuisance. Manchester's musical life does not stop at a municipal border, and neither does Birmingham's. A band can form in a town that is socially and economically part of a larger urban area while still having a perfectly good local identity of its own.

I used the OECD's [Functional Urban Areas](https://www.oecd.org/en/data/datasets/oecd-definition-of-cities-and-functional-urban-areas.html), or FUAs. An FUA combines an urban centre with the surrounding places connected to it through commuting. It is a consistent geographic indicator, which is the sort of thing a comparison needs.

I took the ten largest UK FUAs in the OECD's 2024 population data: London, Manchester, Birmingham, Leeds, Glasgow, Liverpool, Sheffield, Newcastle, Bristol and Leicester.

Bands were assigned by reviewed formation place. That puts Joy Division's Salford origin inside Manchester FUA and The 1975's Wilmslow origin there too, because the frozen OECD assigns Salford and Cheshire East to the Manchester functional area. I did not know about Salford or Wilmslow, I'm not THAT big of a nerd.

## Define a musical act

I excluded solo artists because I was interested in "groups of minds" rather than individual star personalities. Forming a band depends on collaboration and local networks in a way that a solo career does not necessarily capture. It also avoids counting the same success twice when a musician becomes famous with a band and then again alone. Named duos and electronic acts still count when they operate as groups. That decision is debatable, but at least I made it explicit.

## Build ten tiny catalogues

I selected ten bands for each FUA, giving me 100 bands in total. Making every list the same length prevents London from winning simply because I happened to write down seventeen London bands from memory, and only one from Leicester.

This is the largest weakness in the exercise. The lists mix my original shortlist –which was heavily influenced by my adolescence,– automated candidates and later editorial additions. Equalising the number of bands controls the selection size, but it is definitely not a random sample.

The result is therefore a comparison of these catalogues, not a rigorous census of British music. I may have missed your favorite band, and at the same time committed additional statistical sins.

I checked each origin. The final selection has 99 high-confidence assignments and one dubious case: Chumbawamba. It was formed either in Burnley or in Leeds. I kept Leeds, and tested the result with and without the band and Leeds's rank did not change.

## How do we measure popularity?

Popularity is the slipperiest word in this project. I first tried Google Trends, using The Beatles as a common reference point for every band. This produced "numbers", which is not the same as producing a measurement. Google samples the data and normalizes every request against the other searches in that request. Comparing a hundred bands meant splitting them into batches and repeatedly carrying The Beatles from one batch to the next. It had the benefit of going like 20 years into the past, but everything felt flaky and irreproduceable and I lost interest in this approach pretty quick.

Spotify gave me a couple of numbers that could be captured for every selected band at the same moment: followers and monthly listeners. Followers accumulate slowly, like a stock of people who pressed a button at some point. Monthly listeners are a moving window: [Spotify counts](https://support.spotify.com/na-en/artists/article/audience-segments/) the people who heard an artist during the previous 28 days, whether they chose the artist themselves or encountered them through programmed listening.

I tried both with a smaller 50-band version of the study. The two measures produced the same top three cities and a rank correlation of 0.95. That looked reassuring until I compared the same artists at two different dates. All 50 had gained followers, but only 28 had gained monthly listeners, and the rank correlation between the two kinds of change was only 0.23. As expected, followers behave like accumulated reputation, and monthly listeners behave more like current attention, very sensitive to platform trends.

My original question was about the reach these bands have today, so I chose monthly listeners. I froze the figures on 18 July 2026.

Whatever cultural impact this index manages to capture belongs to the summer of 2026. If we run the same exercise in 2016 or 2036 and the order could look very different.

The numerator and denominator are also two years apart. Using the latest complete OECD population data from 2024 leaves an explicit timing mismatch in the comparison.

I also tested a year of English Wikipedia pageviews against Spotify followers in a much larger band catalogue. The two were broadly related, with a rank correlation of 0.77, but not interchangeable. A Wikipedia visit can be triggered by a death, a documentary, an argument, or the need to remember who played bass. Combining pageviews, followers and listeners into one "popularity score" would have led me further into insanity in exchange for a more impressive-looking decimal.

These are global numbers. They do not tell us how many people in Sheffield listen to Pulp. They also cannot be added into a count of unique humans: one person who listened to Arctic Monkeys, Pulp and Def Leppard will appear in the three artist total.

So the calculation is an index. The numerator is global Spotify attention in July 2026. The denominator is local FUA population in 2024. Dividing one by the other helps compare places of very different sizes, but it does not create a local listening rate. No resident of Sheffield was asked to sacrifice 75.3 Spotify listeners for the purposes of this research.

Keeping those limits in mind, I calculated three things:

1. the combined monthly listeners of all ten selected bands
2. the same total divided by FUA population
3. the population-normalized total after removing each FUA's largest selected band

The second is the main result. The third is a sensitivity test: does a city still look strong after we ignore its biggest act?

## London wins the obvious contest

Before adjusting for population, London is enormous. Its ten selected bands have a combined 360.8 million monthly listeners. Manchester follows with 138.7 million, then Sheffield with 93.7 million.

This is not surprising as London has more than 12 million people in its FUA and a very large music industry. Asking it to compete on raw totals is like inviting a stadium act to an open-mic night in a pub.

![Combined monthly listeners for ten selected bands in each FUA](artifacts/charts/chart_02_raw_fua_totals.png)

The composition of those totals is more revealing. Every bar below is the same length, but the pieces inside it show how much each selected band contributes. Some catalogues are fairly spread out. Others contain one very large, very famous entry.

![Share of each FUA's selected monthly-listener total by band](artifacts/charts/chart_01_fua_band_share_stack.png)

The Beatles provide 53% of Liverpool's selected total. Arctic Monkeys provide 56% of Sheffield's. Oasis account for 29% of Manchester's, while London's largest selected act, Coldplay, supplies 26%. The Animals make up 76% of Newcastle's total. Newcastle is hiding an elephant in the room, an elephant that can play "House of the Rising Sun".

## But normalization changes the order

When I divide the same totals by FUA population, Sheffield moves to first place. Liverpool is second and Manchester third. London falls to fourth, followed by Birmingham.

The full order is:

1. Sheffield
2. Liverpool
3. Manchester
4. London
5. Birmingham
6. Glasgow
7. Bristol
8. Newcastle
9. Leeds
10. Leicester

![Selected global Spotify reach divided by FUA population](artifacts/charts/chart_03_fua_population_normalized_total.png)

That is the answer to the narrow question I actually calculated. Among these ten FUAs, using these ten-band catalogues, this Spotify snapshot and this population denominator, Sheffield has the largest selected-band Spotify footprint relative to population.

There are enough caveats in that sentence to trip you up. But they matter.

Liverpool's particular number is heavily Beatles-shaped. Same situation for Newcastle with The Animals.

The cutoff at the ten largest FUAs is not neutral either: Oxford and Crawley point to two very different ways smaller places can complicate the answer (see [possible avenues](#1-what-happens-beyond-the-ten-largest-urban-areas)).


## Scene depth?

For each FUA, I removed its most-listened selected band and repeated the population calculation with the remaining nine.

I originally called this "scene depth". But that's too ambitious because removing one band cannot reveal the true depth of a city's music scene, especially when the other nine were selected rather than sampled. A more accurate name is a less-catchy "dominant-band sensitivity within the selected catalogue".

Sheffield stays first after Arctic Monkeys are removed. Manchester moves from third to second, even without Oasis, while Liverpool moves from second to third once The Beatles are removed. London and Birmingham stay fourth and fifth.

![Raw, population-normalized and dominant-band-excluded ranks](artifacts/charts/chart_04_raw_normalized_scene_depth_fua_ranks.png)

This result makes Sheffield interesting. Its primary total is concentrated in Arctic Monkeys, yet the other nine selected bands still produce the strongest population-normalized total in the comparison. Manchester also looks less dependent on one act. Birmingham's selected catalogue is the least concentrated of the ten: ELO contributes about 22% of its total.

## So, which city wins?

It depends, annoyingly. If we consider raw Spotify reach, London. If it's relative to population (my question), even without its biggest export, Sheffield comes first.

Sheffield performs strongly in both published views of this selected catalogue. Manchester combines a large raw total with less dependence on its biggest selected act. London has the largest absolute footprint but loses its automatic advantage once population enters the calculation.

None of this makes Sheffield objectively Britain's best music city. The data do not measure local listening, cultural importance, historical influence or every band. They certainly do not prove that living in Sheffield causes musical success. It seems to be, however, another one of those places with bad weather and decaying industry that has produced an unusually high number of famous musical acts.


## Interactive Version

I also built an [interactive version of the project](https://www.danielpradilla.info/uk-music-cities/). It uses a much larger frozen catalogue of 1,000 Spotify artist pages drawn from a Wikidata UK musical-group candidate set and ranked by monthly listeners after reviewed identity, eligibility and duplicate-entity filtering, rather than the balanced 100-band list used in this study. You can search for a band or place, compare monthly listeners or followers, and switch between raw formation-place totals and population-normalized FUA results. The raw view covers 749 bands with a resolved formation place; the stricter FUA view covers 663 bands across 59 urban areas and leaves missing mappings explicit. Because this is an unbalanced popularity-first catalogue rather than ten selected bands per city, it is an exploratory sensitivity view, not a reproduction of the formal ranking or a census of every UK band.

## Code

The code, notebooks, frozen data and instructions for reproducing the study are in the [UK Music Cities repository on GitHub](https://github.com/danielpradilla/uk-music-cities).





## Past and future avenues of exploration

Finishing this version left me with several questions I would like to pursue.


### 1. What happens beyond the ten largest urban areas?

I started looking into this in a [notebook that applies the same ten-band method to the twenty largest UK urban areas](https://github.com/danielpradilla/uk-music-cities/blob/master/notebooks/experiments/08_uk_bands_top20_fua_final_structure.ipynb). Oxford comes first. Radiohead provides about 54% of its selected monthly listeners, but Oxford remains first even after Radiohead is removed.

A different [notebook starts with the 100 most-listened bands and then maps their origins](https://github.com/danielpradilla/uk-music-cities/blob/master/notebooks/experiments/09_uk_bands_top100_popularity_first_fua.ipynb). In that version Crawley ranks very highly because of the Cure, its only selected band. Remove the Cure and Crawley's total falls to zero. Oxford and Crawley are interesting for different reasons, so they should not be squeezed into the same league table.

### 2. What changes if solo artists are included?

This study is about bands, so it leaves out solo artists by design. I have not built this notebook yet. The next step would be to run the comparison again with solo acts included and see which cities and genres gain the most. That deserves its own list and its own result rather than being slipped into this one.

### 3. How much does the choice of bands change the result?

Giving every city ten bands makes the arithmetic even, but it does not make the lists neutral. Some bands came from my memory and taste. Others came from database searches or were added later when I found gaps.

I started looking into this in a [notebook that replaces my editorial lists with the ten most-listened eligible bands for each city](https://github.com/danielpradilla/uk-music-cities/blob/master/notebooks/experiments/24_uk_bands_catalogue_selection_sensitivity.ipynb). Thirteen of the 80 selections differ in the cities that can be compared, but all eight primary ranks stay in place. The dominant-band-excluded ranking moves a little more. A second [notebook tries 32 reasonable versions of the ranking](https://github.com/danielpradilla/uk-music-cities/blob/master/notebooks/experiments/16_uk_bands_specification_multiverse.ipynb). It shows how much the answer can move when I change the list, the Spotify measure, the place assignments or the calculation.

### 4. What do Spotify's numbers tell us?

[Spotify's monthly-listener figure](https://support.spotify.com/na-en/artists/article/audience-segments/) covers the previous 28 days. Followers build up over a much longer period. Neither figure tells us where those people live, and one person can appear in the totals for several bands.

I started looking into this in a [notebook that compares the same 50 bands at two dates](https://github.com/danielpradilla/uk-music-cities/blob/master/notebooks/experiments/22_uk_bands_longitudinal_reach.ipynb). Every band gained followers, while monthly listeners rose for some and fell for others. Another [notebook compares Spotify followers with Wikipedia visits](https://github.com/danielpradilla/uk-music-cities/blob/master/notebooks/experiments/23_uk_bands_beyond_spotify.ipynb). The measures are related, but they are not interchangeable.

The better follow-up would collect the same figures every month for at least 18 to 24 months and note releases, tours, reissues and viral moments as they happen. Two dates are a comparison, not a trend.

### 5. Where is a band actually from?

This sounds simple until the sources disagree. The [origin review](https://github.com/danielpradilla/uk-music-cities/blob/master/reference/final_origin_confidence_audit_20260822.md), for example, found accounts that place Chumbawamba's formation in Burnley and others that place it in the Armley squat in Leeds.

I started testing how different mapping choices affect the ranking in the [32-version notebook](https://github.com/danielpradilla/uk-music-cities/blob/master/notebooks/experiments/16_uk_bands_specification_multiverse.ipynb). A fuller study could compare members' home towns, the first rehearsal, the first concert and the place where a band found its audience. It may be more honest to keep several places than to force every band into one city.

### 6. What makes a music scene more than one famous band?

A city can score highly because of one enormous act. That is not the same as having many successful bands or a strong network of venues, labels and musicians.

I started looking into this in the [scene-depth notebook](https://github.com/danielpradilla/uk-music-cities/blob/master/notebooks/experiments/17_uk_bands_scene_depth_and_concentration.ipynb). Other notebooks look at [bands by decade](https://github.com/danielpradilla/uk-music-cities/blob/master/notebooks/experiments/18_uk_bands_generations_by_decade.ipynb), [genre histories](https://github.com/danielpradilla/uk-music-cities/blob/master/notebooks/experiments/19_uk_bands_genre_city_histories.ipynb), [venues and other music infrastructure](https://github.com/danielpradilla/uk-music-cities/blob/master/notebooks/experiments/20_uk_bands_scene_infrastructure.ipynb), and [connections through members and record labels](https://github.com/danielpradilla/uk-music-cities/blob/master/notebooks/experiments/21_uk_bands_band_networks.ipynb). These are leads, not explanations. A count of today's venues cannot tell us why a scene emerged forty years ago.


---
