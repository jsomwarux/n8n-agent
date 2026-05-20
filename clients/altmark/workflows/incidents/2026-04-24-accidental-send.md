# 2026-04-24 — Accidental COI outreach send

During Altmark COI workflow setup, the workflow was activated to test a webhook trigger while the Gmail nodes were still enabled. When the Google Sheets credential started working, the workflow ran end-to-end and sent 58 real tenant emails before hitting an unrelated error at the log-write step.

## Impact
- **Sent from:** `jtsomwaru@gmail.com` (JT personal test credential — was meant to be swapped to `insurance@altmarkgroup.com` before any real outreach)
- **CC on every email:** `yair@altmarkgroup.com`, `matt@altmarkgroup.com` (per workflow spec)
- **Template used:** Initial Request
- **Alert Log NOT updated** — execution errored at `Append to Alert Log` step after Gmail send succeeded. Without backfill, re-running the workflow would duplicate-email these 58 tenants.

## Remediation
- Workflow deactivated immediately after detection.
- Alert Log backfill file generated: `2026-04-24-alert-log-backfill.tsv` — paste into `COI Alert Log` tab starting at A2 to mark these 58 as Initial Request-sent today.
- JT to brief Yair + Matt; they will already see 58 Altmark-branded requests in their inbox from `jtsomwaru@gmail.com`.

## Tenants emailed (58)

| Tenant | Entity | Property | Unit | Email To |
|---|---|---|---|---|
| Mike's Tire & Auto Repair Shop Corp. | Markland 153 LLC | 153 W 2nd Street, Mount Vernon, NY 10550 | Single Tenant | rebekahgarabito@gmail.com |
| The Guidance Center of Westchester, Inc. | 256 Washington Street LLC | 256 Washington Street, Mount Vernon, NY 10553 | MAIN | dadames@theguidancecenter.org |
| RS (Dolce) Woodworking | 256 Washington Street LLC | 256 Washington Street, Mount Vernon, NY 10553 | BB-1C | ron@rs-woodworking.com |
| Precision Air Control | 256 Washington Street LLC | 256 Washington Street, Mount Vernon, NY 10553 | MB-1D | precisionair@optonline.net |
| Classic New York USA Inc. | 256 Washington Street LLC | 256 Washington Street, Mount Vernon, NY 10553 | MB-1A | md.alam2253@gmail.com |
| Judy Mannarino | 728 East Holdings LLC | 728 East 136th Street, Bronx, NY 10454 | 4E | judymannarino@gmail.com |
| Maxwell & Cohen Photography LLC | 728 East Holdings LLC | 728 East 136th Street, Bronx, NY 10454 | 305 | mandy@maxandcophoto.com |
| Bernice Garo Interiors | 728 East Holdings LLC | 728 East 136th Street, Bronx, NY 10454 | 2B-2 | bernice.garo3@gmail.com |
| Todos Services | 728 East Holdings LLC | 728 East 136th Street, Bronx, NY 10454 | Rear-D | stalintodos1970@gmail.com |
| Todos Design | 728 East Holdings LLC | 728 East 136th Street, Bronx, NY 10454 | Rear-A | jairopaulinop0416@gmail.com |
| The Five Group LLC | 728 East Holdings LLC | 728 East 136th Street, Bronx, NY 10454 | 403 | ssb5001@aol.com |
| The HOPE Program, Inc. | Markland 1360 LLC | 1360 Garrison Avenue, Bronx, NY 10474 | #2 | ghaxhillari@thehopeprogram.org |
| Number One Contracting Corp. | Markland 1360 LLC | 1360 Garrison Avenue, Bronx, NY 10474 | Garage | aftabshahnoc@gmail.com |
| Vial Electric | Markland 388 LLC | 388 Canal Place / 389 Rider Ave Bronx, NY 10451 | GF-B | fab@vialelectric.com |
| Foreign Car Repair Specialists Inc | Markland 2507 LLC | 2507 Third Avenue, Bronx, NY 10451 | Single Tenant | pbhaggan@gmail.com |
| Dawgs Life Corp | MPM 67 LLC | 69 Bruckner Boulevard, Bronx, NY 10454 | STORE | brianalhudis@gmail.com |
| Horeb Church | MPM 473 LLC | 473 Willis Avenue, Bronx, NY 10455 | Store-A | sylviedembele72@gmail.com |
| D & C Spa, Inc. | MPM 473 LLC | 473 Willis Avenue, Bronx, NY 10455 | Store-B | davidwen2141@gmail.com |
| Bruckner Garden Corp. (Bricks & Hops) | MPM 65 LLC | 65 Bruckner Boulevard, Bronx, NY 10454 | STORE | rmartinez4495@yahoo.com |
| ADAPT Community Networks | JAM 745 LLC | 747/749/751 East 133rd Street, Bronx, NY 10454 | Apartments | kdisario@adaptcommunitynetwork.org |
| Five Star Machine Corp | 820 East 140th Street LLC | 805 E 139th / 820 East 140th Street, Bronx, NY 10454 | 1A | fivestarshop@msn.com |
| Capital City Movers & Storage, Inc. | 820 East 140th Street LLC | 805 E 139th / 820 East 140th Street, Bronx, NY 10454 | 820-201 | info@capitalcitymovers.us |
| Lucidity Awards & Signage Corp. | 820 East 140th Street LLC | 805 E 139th / 820 East 140th Street, Bronx, NY 10454 | 3A | margaret@luciditysigns.com |
| UPNYC THR33 LLC | Markland Lincoln JV LLC | 2490 Third Avenue, Bronx, NY 10451 | STORE | slow@upnyc158.com |
| NewBridge Data | Markland 713 LLC | 713 East 133rd Street, Bronx, NY 10454 | Single Tenant | technicians@newbridgedata.com |
| G.E.J. Premiere LLC | 53 Bruckner Owner LLC | 53 Bruckner Boulevard, Bronx, NY 10454 | STORE | echezona.eche@gmail.com |
| John Sheppard Studio | Bronx Canvas LLC | 728 East 136th Street, Bronx, NY 10454 | 303 | info@johnsheppard.net |
| Matthew Lucks | Bronx Canvas LLC | 728 East 136th Street, Bronx, NY 10454 | 5C | matt@mattlucks.com |
| Matthew Lucks | Bronx Canvas LLC | 728 East 136th Street, Bronx, NY 10454 | 5D | matt@mattlucks.com |
| Matthew Lucks | Bronx Canvas LLC | 728 East 136th Street, Bronx, NY 10454 | 5E | matt@mattlucks.com |
| Kimberly Ballestros | Bronx Canvas LLC | 728 East 136th Street, Bronx, NY 10454 | 5H | kimballesteros21@gmail.com |
| Samuel Gilchrist | Bronx Canvas LLC | 728 East 136th Street, Bronx, NY 10454 | 5J | sam@pluravida.com |
| Samuel Gilchrist | Bronx Canvas LLC | 728 East 136th Street, Bronx, NY 10454 | 5K | sam@pluravida.com |
| Judy Mannarino | Bronx Canvas LLC | 728 East 136th Street, Bronx, NY 10454 | 5S1 | judymannarino@gmail.com |
| Raymond Hughes | Bronx Canvas LLC | 728 East 136th Street, Bronx, NY 10454 | 6A | hughesraymond90@yahoo.com |
| Desi Santiago | Bronx Canvas LLC | 728 East 136th Street, Bronx, NY 10454 | 6B | desi@desisantiago.com |
| Elizabeth Weiss-Bernarducci | Bronx Canvas LLC | 728 East 136th Street, Bronx, NY 10454 | 6D | elizabethweiss46@icloud.com |
| Salvatore Sferrazza | Bronx Canvas LLC | 728 East 136th Street, Bronx, NY 10454 | 6F | sal@instigate.net |
| Art Studio 6 LLC | Bronx Canvas LLC | 728 East 136th Street, Bronx, NY 10454 | 6J | kathleenzannisacson@gmail.com |
| Darren Kornblut | Bronx Canvas LLC | 728 East 136th Street, Bronx, NY 10454 | 6Q | darren@imageexchange.com |
| Les Ballets Trackadero | Bronx Canvas LLC | 728 East 136th Street, Bronx, NY 10454 | 6T | martinezriveraisabel@gmail.com |
| William Geddes | Bronx Canvas LLC | 728 East 136th Street, Bronx, NY 10454 | 6U | william@williamgeddes.com |
| Chasity Dade | Bronx Canvas Canal LLC | 388 Canal Place / 389 Rider Ave Bronx, NY 10451 | 305 | chasityd88@gmail.com |
| Chelsea Lettsome | Bronx Canvas Canal LLC | 388 Canal Place / 389 Rider Ave Bronx, NY 10451 | 306 | chelsealettsome@gmail.com |
| Eric Payne | Bronx Canvas Canal LLC | 388 Canal Place / 389 Rider Ave Bronx, NY 10451 | 307 | eric@etcreative.live |
| Fatoumata Keita | Bronx Canvas Canal LLC | 388 Canal Place / 389 Rider Ave Bronx, NY 10451 | 309 | fkeita341@gmail.com |
| Aye Diallo | Bronx Canvas Canal LLC | 388 Canal Place / 389 Rider Ave Bronx, NY 10451 | 311 | ayeglamco@gmail.com |
| Genesis Justine Davis | Bronx Canvas Canal LLC | 388 Canal Place / 389 Rider Ave Bronx, NY 10451 | 315 | genesis_davis@icloud.com |
| Khaleyjah Shakira Hogg | Bronx Canvas Canal LLC | 388 Canal Place / 389 Rider Ave Bronx, NY 10451 | 402 | khaleyjahh5@gmail.com |
| Douglas Lister | Bronx Canvas Canal LLC | 388 Canal Place / 389 Rider Ave Bronx, NY 10451 | 406 | douglas@djlister.com |
| Wilfredo Rivera | Bronx Canvas Canal LLC | 388 Canal Place / 389 Rider Ave Bronx, NY 10451 | 407 | wil@grassrootsfitnessproject.com |
| Nicholas Dombroski | Bronx Canvas Canal LLC | 388 Canal Place / 389 Rider Ave Bronx, NY 10451 | 412 | nick.m.dombroski@gmail.com |
| Vitor Rivera Jr | Bronx Canvas Canal LLC | 388 Canal Place / 389 Rider Ave Bronx, NY 10451 | 413 | victormrjr@gmail.com |
| Kadigrah Brisbon | Bronx Canvas Canal LLC | 388 Canal Place / 389 Rider Ave Bronx, NY 10451 | 416 | kadigrah8@gmail.com |
| Her Village | Bronx Canvas Canal LLC | 388 Canal Place / 389 Rider Ave Bronx, NY 10451 | 509 | chantal@wearehervillage.org |
| Deborah Edgar | Bronx Canvas Canal LLC | 388 Canal Place / 389 Rider Ave Bronx, NY 10451 | 510 | Debiedgar@gmail.com |
| Her Village | Bronx Canvas Canal LLC | 388 Canal Place / 389 Rider Ave Bronx, NY 10451 | 512 | chantal@wearehervillage.org |
| Samantha Box | Bronx Canvas Canal LLC | 388 Canal Place / 389 Rider Ave Bronx, NY 10451 | 516 | samantha.nalini.box@gmail.com |