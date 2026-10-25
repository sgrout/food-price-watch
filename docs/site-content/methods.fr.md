# Comment les prévisions sont faites

**De quoi s'agit-il.** Des prévisions des prix des denrées de base par marché, pour les prochains mois, avec un
intervalle honnête et un historique publié de leur fiabilité. Les prix proviennent du Programme alimentaire mondial
(PAM), via le Humanitarian Data Exchange (HDX). C'est un outil gratuit et non commercial pour les organisations qui
n'ont pas leur propre équipe de données. **Ce n'est pas une évaluation officielle** : pour cela, voir
[HungerMap du PAM](https://hungermap.wfp.org) et [FEWS NET](https://fews.net).

**Quelles données une prévision utilise.** Le PAM publie les prix de chaque mois un à deux mois et demi plus tard.
Une prévision faite au cours d'un mois n'utilise donc que les prix publiés à ce moment-là : une prévision faite en
octobre utilise les prix jusqu'en août. Les deux premiers mois affichés (le mois dernier et le mois en cours) sont
des estimations de prix pas encore publiés ; les trois suivants sont des prévisions.

**Comment une prévision est faite.** Un seul modèle apprend de tous les marchés à la fois. Pour chaque denrée et
chaque marché, il regarde l'écart entre le prix et son niveau habituel pour cette période de l'année, l'évolution
du prix au cours des derniers mois, et l'évolution de la même denrée sur les autres marchés du pays. Il donne un
intervalle de prix probables, pas un seul chiffre. Cet intervalle est ensuite corrigé à l'aide des erreurs passées
du modèle, en n'utilisant que les erreurs déjà connues à ce moment-là.

**Comment lire l'intervalle.** L'intervalle à 80 % signifie : si l'historique se confirme, le prix réel s'y
trouvera environ 8 fois sur 10. La page sur la fiabilité des prévisions montre combien de fois c'est vraiment arrivé.

**Ce qu'est une flambée des prix.** Un prix nettement au-dessus de son niveau habituel pour cette période de
l'année : au moins un écart-type au-dessus d'une tendance saisonnière estimée sur les dix dernières années. Les
niveaux sont normal, stress, alerte et crise, d'après l'Alerte aux flambées des prix (ALPS) du PAM. Notre version
diffère de celle du PAM sur trois points : elle utilise des prix relatifs (logarithmes), une fenêtre de dix ans, et
uniquement les données disponibles à chaque date (le PAM estime la tendance sur toute la série). Les flambées
passées affichées ici ne correspondent donc pas toujours aux graphiques du PAM.

**Contrôles des données.** Une valeur qui saute puis revient entièrement le mois suivant est marquée comme erreur
de données et n'est pas utilisée, dès que le mois suivant est publié. Une forte hausse du dernier mois est marquée
comme pas encore confirmée. Les denrées que le PAM a renommées ne sont reliées que si le niveau des prix
correspond. Rien n'est corrigé en silence.

**Limites connues.**
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

**Source et licence.** Programme alimentaire mondial, prix des denrées alimentaires sur HDX, CC BY-IGO.
