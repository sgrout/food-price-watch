# Comment les prévisions sont faites

## De quoi s'agit-il

Des prévisions des prix des denrées de base par marché, pour les prochains mois, avec un
intervalle honnête et un historique publié de leur fiabilité. Les prix proviennent du Programme alimentaire mondial
(PAM), via le Humanitarian Data Exchange (HDX). C'est un outil gratuit et non commercial pour les organisations qui
n'ont pas leur propre équipe de données. **Ce n'est pas une évaluation officielle** : pour cela, voir
[HungerMap du PAM](https://hungermap.wfp.org) et [FEWS NET](https://fews.net).

## Quelles données une prévision utilise

Le PAM publie les prix de chaque pays un à plusieurs mois plus tard, et ce délai varie selon le pays et le mois. Une
prévision utilise le mois le plus récent publié par le PAM pour ce pays : la date « données jusqu'à » peut donc
différer d'un pays à l'autre. Les mois pas encore publiés sont affichés comme des estimations ; les trois mois suivants
sont des prévisions. Si le mois le plus récent d'un pays date de plus de quatre mois, nous ne faisons pas de prévision
pour ce pays jusqu'à une nouvelle publication du PAM : ses prix restent sur le site. Dans les tests sur le passé,
chaque prévision ne pouvait utiliser que le mois réellement publié à ce moment-là.

## Comment une prévision est faite

Un seul modèle apprend de tous les marchés à la fois. Pour chaque denrée et
chaque marché, il regarde l'écart entre le prix et son niveau habituel pour cette période de l'année, l'évolution
du prix au cours des derniers mois, et l'évolution de la même denrée sur les autres marchés du pays. Il donne un
intervalle de prix probables, pas un seul chiffre. Cet intervalle est ensuite corrigé à l'aide des erreurs passées
du modèle, en n'utilisant que les erreurs déjà connues à ce moment-là.

## Comment lire l'intervalle

L'intervalle à 80 % signifie : si l'historique se confirme, le prix réel s'y
trouvera environ 8 fois sur 10. La page sur la fiabilité des prévisions montre combien de fois c'est vraiment arrivé.

Comment l'utiliser : la valeur la plus probable indique la direction (par exemple une baisse après la récolte) ; la
borne haute montre jusqu'où le prix pourrait raisonnablement monter, par exemple comme marge pour prévoir un budget.
Dans un même pays, un intervalle plus large signifie moins de certitude pour ce marché.

## Pourquoi les intervalles sont larges

Les intervalles sont larges parce que les prix alimentaires varient vraiment autant, et nous préférons le montrer
plutôt que de paraître plus précis que nous ne le sommes. Un intervalle plus étroit aurait l'air meilleur, mais il
se tromperait plus souvent. Trois choses les élargissent :

- **Les prix varient beaucoup.** Autour de la récolte et de la période de soudure, les prix des denrées de base
  peuvent monter ou baisser fortement en quelques mois, et le moment change d'une année à l'autre.
- **Le prix le plus récent est déjà ancien.** Le PAM publie les prix un à plusieurs mois plus tard : « le mois
  prochain » se situe donc souvent deux ou trois mois après le dernier prix connu.
- **Certains marchés publient de façon irrégulière.** Si un marché n'a pas publié de prix depuis un moment, la
  prévision part d'un prix plus ancien et son intervalle est encore plus large ; le texte le signale alors.

Dans les tests sur 2023 et après, l'erreur typique pour les denrées seules (la moitié des erreurs étaient plus petites)
était d'environ 5 % pour le mois écoulé, 9 % pour le mois prochain et 13 % à trois mois. Pour le panier, qui utilise
encore la méthode précédente, elle était d'environ 4 %, 10 % et 16 %.

## Ce qu'est une flambée des prix

Un prix nettement au-dessus de son niveau habituel pour cette période de
l'année : au moins un écart-type au-dessus d'une tendance saisonnière estimée sur les dix dernières années. Les
niveaux sont normal, stress, alerte et crise, d'après l'Alerte aux flambées des prix (ALPS) du PAM. Notre version
diffère de celle du PAM sur trois points : elle utilise des prix relatifs (logarithmes), une fenêtre de dix ans, et
uniquement les données disponibles à chaque date (le PAM estime la tendance sur toute la série). Les flambées
passées affichées ici ne correspondent donc pas toujours aux graphiques du PAM.

## Panier alimentaire

Pour certains marchés, le site montre aussi le coût d'un panier de base simple pour une
personne pendant un mois, fondé sur une ration alimentaire type du PAM (12 kg de céréales, 1,8 kg de légumineuses,
0,75 l d'huile), avec seulement les denrées que le PAM suit assez longtemps dans le pays. Il est établi par Staple
Signals et **n'est pas un panier minimum de dépenses officiel**. Son intervalle combine les prévisions des denrées
qui le composent, en tenant compte de la façon dont leurs erreurs passées ont évolué ensemble : il est plus large
quand les denrées ont tendance à monter et baisser ensemble.

## Écart avec le prix national

Pour chaque denrée, la page compare le prix du marché avec le prix médian de la même denrée sur les autres marchés
du pays ce mois-là (au moins cinq marchés), et avec l'écart habituel de ce marché au cours des trois années
précédentes. Les marchés éloignés sont souvent plus chers en permanence : ce qui compte, c'est un écart qui grandit.
Dans les zones sous blocus ou coupées du reste, les prix peuvent s'écarter de ceux du reste du pays, et une moyenne
nationale cache justement ces endroits. Un marché est signalé quand son prix est au moins 25 % au-dessus de la
médiane nationale et nettement au-dessus de son écart habituel. C'est une description des données, pas une
prévision ni une alerte éprouvée : une erreur de données peut avoir le même aspect.

## Marchés qui ont cessé de publier

Un marché qui n'a publié aucun prix, pour aucune denrée, depuis deux mois ou plus est affiché comme tel, avec ses
derniers prix, au lieu de disparaître. Les mois sont comptés à partir du dernier mois publié par la plupart des
marchés du pays, pour que le délai de publication habituel du PAM ne compte pas comme un silence. Dans les zones de
conflit, l'absence de données peut être un premier signe de difficultés, mais elle peut aussi avoir d'autres causes,
comme une pause du suivi ou un changement de la liste des marchés suivis par le PAM.

## Contrôles des données

Une valeur qui saute puis revient entièrement le mois suivant est marquée comme erreur
de données et n'est pas utilisée, dès que le mois suivant est publié. Une forte hausse du dernier mois est marquée
comme pas encore confirmée. Les denrées que le PAM a renommées ne sont reliées que si le niveau des prix
correspond. Rien n'est corrigé en silence.

## Limites connues

- Les alertes de *nouvelles* flambées n'ont pas encore fait leurs preuves : la probabilité de flambée n'est
  affichée que pour le mois prochain, car au-delà elle a fait moins bien que la simple fréquence habituelle des
  flambées.
- Les intervalles larges (95 %) sont peu fiables, surtout après une hausse soudaine ; fiez-vous à l'intervalle à 80 %.
- Le PAM peut réviser des mois passés ; cet historique ne peut pas être reconstitué, donc le test sur le passé
  utilise les valeurs d'aujourd'hui.
- Certains marchés publient des prix identiques pendant de nombreux mois ; ils peuvent être réels ou reportés, et
  ces séries paraissent plus calmes qu'elles ne le sont.
- Les marchés des zones de conflit publient moins souvent, surtout pendant les crises. Les marchés qui ont publié un
  prix moins de 9 mois sur les 12 derniers sont signalés.
- Les prix sont en monnaie locale, non corrigés de l'inflation.

## Source et licence

Programme alimentaire mondial, prix des denrées alimentaires sur HDX, CC BY-IGO.
