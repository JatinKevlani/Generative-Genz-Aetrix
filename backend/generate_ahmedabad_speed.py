"""
Generate ahmedabad_traffic_speed.csv — Ahmedabad equivalent of nyc_traffic_speed.csv.

Produces ~1.7 M rows (200 links × 8 640 five-minute intervals in 30 days).
Columns mirror the original NYC file:
  Id, Speed, TravelTime, Status, DataAsOf, linkId, linkName,
  EncodedPolyLine, EncodedPolyLineLvls, Borough, linkPoints
"""

import csv
import random
import math
import os
from datetime import datetime, timedelta

# ── Ahmedabad road-link definitions ─────────────────────────────────────────
# Each entry:
#   linkId, linkName, zone, (start_lat, start_lng, end_lat, end_lng),
#   base_speed (km/h), segment_length_km

LINKS = [
    # ── West Zone ──
    (101, "SG Highway NB — Iskcon to Bopal",             "West",  (23.0300, 72.5070, 23.0050, 72.5100), 55, 3.2),
    (102, "SG Highway SB — Bopal to Iskcon",             "West",  (23.0050, 72.5100, 23.0300, 72.5070), 55, 3.2),
    (103, "SG Highway NB — Bopal to SP Ring Rd",         "West",  (23.0050, 72.5100, 22.9800, 72.5200), 50, 3.0),
    (104, "SG Highway SB — SP Ring Rd to Bopal",         "West",  (22.9800, 72.5200, 23.0050, 72.5100), 50, 3.0),
    (105, "SG Highway NB — Iskcon to Vastrapur",         "West",  (23.0300, 72.5070, 23.0400, 72.5280), 48, 2.8),
    (106, "SG Highway SB — Vastrapur to Iskcon",         "West",  (23.0400, 72.5280, 23.0300, 72.5070), 48, 2.8),
    (107, "Ashram Rd NB — Paldi to Income Tax",          "West",  (23.0080, 72.5650, 23.0230, 72.5710), 35, 2.0),
    (108, "Ashram Rd SB — Income Tax to Paldi",          "West",  (23.0230, 72.5710, 23.0080, 72.5650), 35, 2.0),
    (109, "CG Road EB — Stadium to Swastik",             "West",  (23.0310, 72.5600, 23.0310, 72.5720), 30, 1.5),
    (110, "CG Road WB — Swastik to Stadium",             "West",  (23.0310, 72.5720, 23.0310, 72.5600), 30, 1.5),
    (111, "Judges Bungalow Rd NB — Bodakdev to Vastrapur","West", (23.0350, 72.5030, 23.0450, 72.5150), 32, 1.8),
    (112, "Judges Bungalow Rd SB — Vastrapur to Bodakdev","West", (23.0450, 72.5150, 23.0350, 72.5030), 32, 1.8),
    (113, "Premchandnagar Rd EB — Satellite to Jodhpur",  "West", (23.0200, 72.5050, 23.0200, 72.5200), 28, 1.6),
    (114, "Premchandnagar Rd WB — Jodhpur to Satellite",  "West", (23.0200, 72.5200, 23.0200, 72.5050), 28, 1.6),
    (115, "Sindhu Bhawan Rd NB — Thaltej to SG Hwy",      "West", (23.0470, 72.4990, 23.0350, 72.5070), 38, 1.9),
    (116, "Sindhu Bhawan Rd SB — SG Hwy to Thaltej",      "West", (23.0350, 72.5070, 23.0470, 72.4990), 38, 1.9),
    (117, "132 Ft Ring Rd EB — Satellite to Shyamal",     "West", (23.0150, 72.5050, 23.0150, 72.5250), 42, 2.3),
    (118, "132 Ft Ring Rd WB — Shyamal to Satellite",     "West", (23.0150, 72.5250, 23.0150, 72.5050), 42, 2.3),
    (119, "Science City Rd EB — Sola to Science City",    "West", (23.0700, 72.5100, 23.0700, 72.5300), 35, 2.1),
    (120, "Science City Rd WB — Science City to Sola",    "West", (23.0700, 72.5300, 23.0700, 72.5100), 35, 2.1),

    # ── East Zone ──
    (201, "Naroda Rd NB — Sarangpur to Naroda",           "East", (23.0350, 72.6050, 23.0700, 72.6350), 33, 4.5),
    (202, "Naroda Rd SB — Naroda to Sarangpur",           "East", (23.0700, 72.6350, 23.0350, 72.6050), 33, 4.5),
    (203, "Vastral Rd EB — Amraiwadi to Vastral",         "East", (23.0000, 72.6100, 23.0000, 72.6400), 28, 3.2),
    (204, "Vastral Rd WB — Vastral to Amraiwadi",         "East", (23.0000, 72.6400, 23.0000, 72.6100), 28, 3.2),
    (205, "CTM Rd NB — Rakhial to CTM",                   "East", (23.0150, 72.6050, 23.0300, 72.6180), 25, 2.0),
    (206, "CTM Rd SB — CTM to Rakhial",                   "East", (23.0300, 72.6180, 23.0150, 72.6050), 25, 2.0),
    (207, "Odhav Ring Rd EB — Odhav to Nikol",            "East", (22.9900, 72.6300, 22.9950, 72.6600), 40, 3.5),
    (208, "Odhav Ring Rd WB — Nikol to Odhav",            "East", (22.9950, 72.6600, 22.9900, 72.6300), 40, 3.5),
    (209, "Nikol Rd NB — Nikol Gam to SP Ring Rd",        "East", (23.0400, 72.6550, 23.0600, 72.6700), 30, 2.5),
    (210, "Nikol Rd SB — SP Ring Rd to Nikol Gam",        "East", (23.0600, 72.6700, 23.0400, 72.6550), 30, 2.5),
    (211, "Rabari Colony Rd NB — Bapunagar to Saijpur",   "East", (23.0380, 72.6280, 23.0550, 72.6380), 22, 2.0),
    (212, "Rabari Colony Rd SB — Saijpur to Bapunagar",   "East", (23.0550, 72.6380, 23.0380, 72.6280), 22, 2.0),
    (213, "Krishnanagar Rd EB — Rakhial to Krishnanagar", "East", (23.0150, 72.6200, 23.0180, 72.6400), 26, 2.2),
    (214, "Krishnanagar Rd WB — Krishnanagar to Rakhial", "East", (23.0180, 72.6400, 23.0150, 72.6200), 26, 2.2),
    (215, "Isanpur Rd NB — Isanpur to Vatva",             "East", (22.9800, 72.6150, 22.9950, 72.6300), 30, 2.0),
    (216, "Isanpur Rd SB — Vatva to Isanpur",             "East", (22.9950, 72.6300, 22.9800, 72.6150), 30, 2.0),
    (217, "New Naroda Rd EB — Naroda to New Naroda",      "East", (23.0700, 72.6350, 23.0800, 72.6600), 32, 3.0),
    (218, "New Naroda Rd WB — New Naroda to Naroda",      "East", (23.0800, 72.6600, 23.0700, 72.6350), 32, 3.0),
    (219, "GIDC Rd EB — Odhav GIDC to Vatva GIDC",       "East", (22.9850, 72.6200, 22.9800, 72.6450), 35, 2.8),
    (220, "GIDC Rd WB — Vatva GIDC to Odhav GIDC",       "East", (22.9800, 72.6450, 22.9850, 72.6200), 35, 2.8),

    # ── Central Zone / Walled City ──
    (301, "Relief Rd NB — Kalupur to Lal Darwaja",        "Central", (23.0290, 72.5880, 23.0230, 72.5800), 18, 1.2),
    (302, "Relief Rd SB — Lal Darwaja to Kalupur",        "Central", (23.0230, 72.5800, 23.0290, 72.5880), 18, 1.2),
    (303, "Gandhi Rd EB — Lal Darwaja to Delhi Darwaja",  "Central", (23.0230, 72.5800, 23.0250, 72.5900), 15, 1.1),
    (304, "Gandhi Rd WB — Delhi Darwaja to Lal Darwaja",  "Central", (23.0250, 72.5900, 23.0230, 72.5800), 15, 1.1),
    (305, "Manek Chowk Rd NB — Manek Chowk to Kalupur",  "Central", (23.0260, 72.5830, 23.0290, 72.5880), 12, 0.8),
    (306, "Manek Chowk Rd SB — Kalupur to Manek Chowk",  "Central", (23.0290, 72.5880, 23.0260, 72.5830), 12, 0.8),
    (307, "Gheekanta Rd EB — Gheekanta to Fernandez Br",  "Central", (23.0280, 72.5770, 23.0300, 72.5850), 14, 0.9),
    (308, "Gheekanta Rd WB — Fernandez Br to Gheekanta",  "Central", (23.0300, 72.5850, 23.0280, 72.5770), 14, 0.9),
    (309, "Jamalpur Rd NB — Jamalpur to Sarangpur",       "Central", (23.0100, 72.5870, 23.0200, 72.5950), 16, 1.3),
    (310, "Jamalpur Rd SB — Sarangpur to Jamalpur",       "Central", (23.0200, 72.5950, 23.0100, 72.5870), 16, 1.3),
    (311, "Shahpur Rd NB — Shah Alam to Shahpur",         "Central", (23.0310, 72.5620, 23.0380, 72.5680), 20, 1.0),
    (312, "Shahpur Rd SB — Shahpur to Shah Alam",         "Central", (23.0380, 72.5680, 23.0310, 72.5620), 20, 1.0),
    (313, "Dariapur Rd EB — Dariapur to Sarangpur",       "Central", (23.0340, 72.5840, 23.0350, 72.5950), 17, 1.2),
    (314, "Dariapur Rd WB — Sarangpur to Dariapur",       "Central", (23.0350, 72.5950, 23.0340, 72.5840), 17, 1.2),
    (315, "Kalupur Station Rd NB — Station to Darwaja",   "Central", (23.0310, 72.5920, 23.0260, 72.5850), 15, 1.0),
    (316, "Kalupur Station Rd SB — Darwaja to Station",   "Central", (23.0260, 72.5850, 23.0310, 72.5920), 15, 1.0),
    (317, "Kankaria Lakefront Rd — Clockwise Loop",       "Central", (23.0070, 72.5920, 23.0050, 72.5950), 20, 2.5),
    (318, "Kankaria Lakefront Rd — Counter-clockwise",    "Central", (23.0050, 72.5950, 23.0070, 72.5920), 20, 2.5),
    (319, "Revdi Bazaar Rd EB — Bhadra to Ellis Br",     "Central", (23.0250, 72.5780, 23.0270, 72.5850), 13, 0.7),
    (320, "Revdi Bazaar Rd WB — Ellis Br to Bhadra",     "Central", (23.0270, 72.5850, 23.0250, 72.5780), 13, 0.7),

    # ── North Zone ──
    (401, "SP Ring Rd NB — Gandhinagar to Adalaj",        "North", (23.1200, 72.5400, 23.1400, 72.5500), 60, 3.5),
    (402, "SP Ring Rd SB — Adalaj to Gandhinagar",        "North", (23.1400, 72.5500, 23.1200, 72.5400), 60, 3.5),
    (403, "Gota Rd NB — Gota to Ognaj",                   "North", (23.1000, 72.5100, 23.1200, 72.5050), 38, 2.5),
    (404, "Gota Rd SB — Ognaj to Gota",                   "North", (23.1200, 72.5050, 23.1000, 72.5100), 38, 2.5),
    (405, "Sola Rd EB — Sola to Science City",            "North", (23.0700, 72.5100, 23.0650, 72.5350), 35, 2.8),
    (406, "Sola Rd WB — Science City to Sola",            "North", (23.0650, 72.5350, 23.0700, 72.5100), 35, 2.8),
    (407, "Chandkheda Rd NB — Motera to Chandkheda",      "North", (23.0850, 72.5900, 23.1050, 72.6000), 33, 2.5),
    (408, "Chandkheda Rd SB — Chandkheda to Motera",      "North", (23.1050, 72.6000, 23.0850, 72.5900), 33, 2.5),
    (409, "Sabarmati Ahm Expy NB — City to NH-48",        "North", (23.0800, 72.5600, 23.1100, 72.5550), 65, 4.0),
    (410, "Sabarmati Ahm Expy SB — NH-48 to City",        "North", (23.1100, 72.5550, 23.0800, 72.5600), 65, 4.0),
    (411, "Motera Stadium Rd EB — Sabarmati to Motera",   "North", (23.0700, 72.5650, 23.0850, 72.5800), 30, 2.0),
    (412, "Motera Stadium Rd WB — Motera to Sabarmati",   "North", (23.0850, 72.5800, 23.0700, 72.5650), 30, 2.0),
    (413, "Koba Rd NB — Koba Circle to GIFT City",        "North", (23.1100, 72.5800, 23.1300, 72.5900), 45, 3.0),
    (414, "Koba Rd SB — GIFT City to Koba Circle",        "North", (23.1300, 72.5900, 23.1100, 72.5800), 45, 3.0),
    (415, "Drive-In Rd EB — Memnagar to Drive-In",        "North", (23.0500, 72.5300, 23.0520, 72.5500), 28, 2.0),
    (416, "Drive-In Rd WB — Drive-In to Memnagar",        "North", (23.0520, 72.5500, 23.0500, 72.5300), 28, 2.0),
    (417, "Usmanpura Flyover NB — Usmanpura to Sabarmati","North", (23.0450, 72.5650, 23.0600, 72.5700), 40, 1.8),
    (418, "Usmanpura Flyover SB — Sabarmati to Usmanpura","North", (23.0600, 72.5700, 23.0450, 72.5650), 40, 1.8),
    (419, "Ranip Rd NB — Sabarmati to Ranip",             "North", (23.0600, 72.5600, 23.0750, 72.5550), 30, 2.0),
    (420, "Ranip Rd SB — Ranip to Sabarmati",             "North", (23.0750, 72.5550, 23.0600, 72.5600), 30, 2.0),

    # ── South Zone ──
    (501, "Narol-Sarkhej Hwy NB — Narol to Sarkhej",     "South", (22.9700, 72.5800, 22.9900, 72.5400), 50, 5.0),
    (502, "Narol-Sarkhej Hwy SB — Sarkhej to Narol",     "South", (22.9900, 72.5400, 22.9700, 72.5800), 50, 5.0),
    (503, "Sarkhej Rd EB — Sarkhej Roza to Juhapura",    "South", (22.9900, 72.5100, 22.9900, 72.5300), 38, 2.2),
    (504, "Sarkhej Rd WB — Juhapura to Sarkhej Roza",    "South", (22.9900, 72.5300, 22.9900, 72.5100), 38, 2.2),
    (505, "Dani Limda Rd NB — Dani Limda to Saraspur",    "South", (23.0050, 72.6000, 23.0200, 72.6050), 22, 1.8),
    (506, "Dani Limda Rd SB — Saraspur to Dani Limda",    "South", (23.0200, 72.6050, 23.0050, 72.6000), 22, 1.8),
    (507, "Maninagar Rd NB — Maninagar to Khokhra",       "South", (22.9950, 72.5950, 23.0100, 72.6000), 25, 1.8),
    (508, "Maninagar Rd SB — Khokhra to Maninagar",       "South", (23.0100, 72.6000, 22.9950, 72.5950), 25, 1.8),
    (509, "SP Ring Rd SB — Sarkhej to Narol",             "South", (22.9900, 72.4900, 22.9600, 72.5800), 55, 6.0),
    (510, "SP Ring Rd NB — Narol to Sarkhej",             "South", (22.9600, 72.5800, 22.9900, 72.4900), 55, 6.0),
    (511, "Vejalpur Rd NB — Vejalpur to Jivraj Park",    "South", (22.9950, 72.5350, 23.0050, 72.5450), 30, 1.5),
    (512, "Vejalpur Rd SB — Jivraj Park to Vejalpur",    "South", (23.0050, 72.5450, 22.9950, 72.5350), 30, 1.5),
    (513, "Pirana Rd EB — Gyaspur to Pirana",            "South", (22.9800, 72.5900, 22.9700, 72.6050), 28, 2.0),
    (514, "Pirana Rd WB — Pirana to Gyaspur",            "South", (22.9700, 72.6050, 22.9800, 72.5900), 28, 2.0),
    (515, "Narol Highway EB — Narol to NH-8",            "South", (22.9600, 72.5850, 22.9600, 72.6100), 45, 2.8),
    (516, "Narol Highway WB — NH-8 to Narol",            "South", (22.9600, 72.6100, 22.9600, 72.5850), 45, 2.8),
    (517, "Vatva GIDC Rd EB — Vatva to GIDC",            "South", (22.9800, 72.6150, 22.9750, 72.6350), 32, 2.2),
    (518, "Vatva GIDC Rd WB — GIDC to Vatva",            "South", (22.9750, 72.6350, 22.9800, 72.6150), 32, 2.2),
    (519, "Lambha Rd NB — Lambha to Narol",              "South", (22.9500, 72.5950, 22.9700, 72.5850), 35, 2.5),
    (520, "Lambha Rd SB — Narol to Lambha",              "South", (22.9700, 72.5850, 22.9500, 72.5950), 35, 2.5),

    # ── Expressways & Bridges ──
    (601, "Ahmedabad–Vadodara Expy EB — City to Vasad",  "Expressway", (23.0100, 72.6200, 22.9200, 73.0000), 80, 10.0),
    (602, "Ahmedabad–Vadodara Expy WB — Vasad to City",  "Expressway", (22.9200, 73.0000, 23.0100, 72.6200), 80, 10.0),
    (603, "Ahmedabad–Gandhinagar Hwy NB — City to GN",   "Expressway", (23.0700, 72.5550, 23.2200, 72.6500), 70, 7.0),
    (604, "Ahmedabad–Gandhinagar Hwy SB — GN to City",   "Expressway", (23.2200, 72.6500, 23.0700, 72.5550), 70, 7.0),
    (605, "Sardar Patel Ring Rd — Outer Clockwise",       "Expressway", (23.1000, 72.5100, 22.9600, 72.5800), 58, 12.0),
    (606, "Sardar Patel Ring Rd — Outer Counter-CW",      "Expressway", (22.9600, 72.5800, 23.1000, 72.5100), 58, 12.0),
    (607, "Nehru Bridge EB — Ashram Rd to Sabarmati E",   "Expressway", (23.0350, 72.5600, 23.0380, 72.5700), 40, 1.0),
    (608, "Nehru Bridge WB — Sabarmati E to Ashram Rd",   "Expressway", (23.0380, 72.5700, 23.0350, 72.5600), 40, 1.0),
    (609, "Ellis Bridge EB — Ashram Rd to Ellis Br",      "Expressway", (23.0280, 72.5650, 23.0310, 72.5750), 35, 1.0),
    (610, "Ellis Bridge WB — Ellis Br to Ashram Rd",      "Expressway", (23.0310, 72.5750, 23.0280, 72.5650), 35, 1.0),
    (611, "Riverfront Rd NB — Sardar Br to Nehru Br",    "Expressway", (23.0200, 72.5680, 23.0350, 72.5650), 45, 2.0),
    (612, "Riverfront Rd SB — Nehru Br to Sardar Br",    "Expressway", (23.0350, 72.5650, 23.0200, 72.5680), 45, 2.0),
    (613, "Sardar Bridge EB — W bank to E bank",          "Expressway", (23.0200, 72.5630, 23.0200, 72.5730), 38, 1.0),
    (614, "Sardar Bridge WB — E bank to W bank",          "Expressway", (23.0200, 72.5730, 23.0200, 72.5630), 38, 1.0),
    (615, "Indira Bridge EB — W bank to E bank",          "Expressway", (23.0500, 72.5600, 23.0500, 72.5700), 38, 1.0),
    (616, "Indira Bridge WB — E bank to W bank",          "Expressway", (23.0500, 72.5700, 23.0500, 72.5600), 38, 1.0),
    (617, "NH-48 NB — Narol to Viramgam turn",           "Expressway", (22.9600, 72.5850, 22.9300, 72.5600), 65, 4.5),
    (618, "NH-48 SB — Viramgam turn to Narol",           "Expressway", (22.9300, 72.5600, 22.9600, 72.5850), 65, 4.5),
    (619, "SG Highway Flyover NB — Helmet to Shivranjani","Expressway",(23.0100, 72.5300, 23.0100, 72.5500), 50, 2.2),
    (620, "SG Highway Flyover SB — Shivranjani to Helmet","Expressway",(23.0100, 72.5500, 23.0100, 72.5300), 50, 2.2),

    # ── Bopal/Ghuma ──
    (701, "Bopal Rd NB — Bopal to Ambli",                "West",  (23.0000, 72.4970, 23.0100, 72.4850), 35, 2.0),
    (702, "Bopal Rd SB — Ambli to Bopal",                "West",  (23.0100, 72.4850, 23.0000, 72.4970), 35, 2.0),
    (703, "Ghuma Rd EB — Ghuma to Bopal",                 "West",  (22.9900, 72.4850, 23.0000, 72.4970), 30, 1.8),
    (704, "Ghuma Rd WB — Bopal to Ghuma",                 "West",  (23.0000, 72.4970, 22.9900, 72.4850), 30, 1.8),
    (705, "South Bopal Rd EB — South Bopal to SP Ring",   "West",  (22.9950, 72.4900, 22.9900, 72.5100), 33, 2.2),
    (706, "South Bopal Rd WB — SP Ring to South Bopal",   "West",  (22.9900, 72.5100, 22.9950, 72.4900), 33, 2.2),
    (707, "Shilaj Rd NB — Shilaj to Thaltej",            "West",  (23.0550, 72.4850, 23.0470, 72.4990), 28, 1.5),
    (708, "Shilaj Rd SB — Thaltej to Shilaj",            "West",  (23.0470, 72.4990, 23.0550, 72.4850), 28, 1.5),
    (709, "Ambli-Bopal Rd EB — Ambli to Bopal Cross",    "West",  (23.0100, 72.4850, 23.0050, 72.5050), 30, 2.0),
    (710, "Ambli-Bopal Rd WB — Bopal Cross to Ambli",    "West",  (23.0050, 72.5050, 23.0100, 72.4850), 30, 2.0),

    # ── BRTS Corridors ──
    (801, "BRTS Kalupur–RTO NB",                          "Central", (23.0290, 72.5880, 23.0230, 72.5600), 25, 3.0),
    (802, "BRTS RTO–Kalupur SB",                          "Central", (23.0230, 72.5600, 23.0290, 72.5880), 25, 3.0),
    (803, "BRTS Maninagar–Narol NB",                      "South",   (22.9950, 72.5950, 22.9600, 72.5850), 28, 4.0),
    (804, "BRTS Narol–Maninagar SB",                      "South",   (22.9600, 72.5850, 22.9950, 72.5950), 28, 4.0),
    (805, "BRTS Chandkheda–RTO NB",                       "North",   (23.1050, 72.5950, 23.0400, 72.5650), 30, 5.0),
    (806, "BRTS RTO–Chandkheda SB",                       "North",   (23.0400, 72.5650, 23.1050, 72.5950), 30, 5.0),
    (807, "BRTS Sola–Naroda EB",                          "North",   (23.0700, 72.5200, 23.0650, 72.6350), 27, 4.5),
    (808, "BRTS Naroda–Sola WB",                          "East",    (23.0650, 72.6350, 23.0700, 72.5200), 27, 4.5),
    (809, "BRTS Vastral–Soni ni Chali EB",                "East",    (23.0000, 72.6350, 23.0120, 72.6100), 24, 3.0),
    (810, "BRTS Soni ni Chali–Vastral WB",                "East",    (23.0120, 72.6100, 23.0000, 72.6350), 24, 3.0),

    # ── Extra roads to reach 200 ──
    (901, "Prahladnagar Rd EB — Prahladnagar to Iscon",   "West",    (23.0150, 72.5100, 23.0200, 72.5250), 30, 1.8),
    (902, "Prahladnagar Rd WB — Iscon to Prahladnagar",   "West",    (23.0200, 72.5250, 23.0150, 72.5100), 30, 1.8),
    (903, "Anand Nagar Rd NB — Anand Nagar to Satellite", "West",    (23.0150, 72.5050, 23.0200, 72.5100), 25, 0.8),
    (904, "Anand Nagar Rd SB — Satellite to Anand Nagar", "West",    (23.0200, 72.5100, 23.0150, 72.5050), 25, 0.8),
    (905, "Shivranjani Flyover NB",                        "West",    (23.0100, 72.5370, 23.0120, 72.5400), 45, 0.5),
    (906, "Shivranjani Flyover SB",                        "West",    (23.0120, 72.5400, 23.0100, 72.5370), 45, 0.5),
    (907, "Navrangpura Rd NB — Navrangpura to Gujarat U", "Central", (23.0350, 72.5550, 23.0420, 72.5500), 22, 1.0),
    (908, "Navrangpura Rd SB — Gujarat U to Navrangpura", "Central", (23.0420, 72.5500, 23.0350, 72.5550), 22, 1.0),
    (909, "Law Garden Rd EB — Law Garden to CG Rd",       "West",    (23.0320, 72.5530, 23.0310, 72.5600), 20, 0.8),
    (910, "Law Garden Rd WB — CG Rd to Law Garden",       "West",    (23.0310, 72.5600, 23.0320, 72.5530), 20, 0.8),
    (911, "Thaltej Rd NB — Thaltej to Sola Overbridge",   "North",   (23.0470, 72.4990, 23.0600, 72.5100), 32, 1.8),
    (912, "Thaltej Rd SB — Sola Overbridge to Thaltej",   "North",   (23.0600, 72.5100, 23.0470, 72.4990), 32, 1.8),
    (913, "Paldi Rd NB — Paldi to Gujarat College",        "West",    (23.0080, 72.5650, 23.0150, 72.5700), 22, 1.0),
    (914, "Paldi Rd SB — Gujarat College to Paldi",        "West",    (23.0150, 72.5700, 23.0080, 72.5650), 22, 1.0),
    (915, "RTO Rd EB — RTO to Gujarat College",            "Central", (23.0350, 72.5500, 23.0300, 72.5600), 25, 1.2),
    (916, "RTO Rd WB — Gujarat College to RTO",            "Central", (23.0300, 72.5600, 23.0350, 72.5500), 25, 1.2),
    (917, "IIM Rd NB — IIM to Vastrapur Lake",             "West",    (23.0290, 72.5250, 23.0380, 72.5300), 28, 1.2),
    (918, "IIM Rd SB — Vastrapur Lake to IIM",             "West",    (23.0380, 72.5300, 23.0290, 72.5250), 28, 1.2),
    (919, "Jodhpur Cross Rd EB — Jodhpur to Satellite",    "West",    (23.0200, 72.5200, 23.0180, 72.5100), 24, 1.1),
    (920, "Jodhpur Cross Rd WB — Satellite to Jodhpur",    "West",    (23.0180, 72.5100, 23.0200, 72.5200), 24, 1.1),
    (921, "Mithakhali Rd NB — Mithakhali to Navrangpura",  "Central", (23.0350, 72.5600, 23.0400, 72.5580), 20, 0.6),
    (922, "Mithakhali Rd SB — Navrangpura to Mithakhali",  "Central", (23.0400, 72.5580, 23.0350, 72.5600), 20, 0.6),
    (923, "Polytechnic Rd NB — Polytechnic to Ambawadi",   "Central", (23.0250, 72.5550, 23.0330, 72.5500), 22, 1.0),
    (924, "Polytechnic Rd SB — Ambawadi to Polytechnic",   "Central", (23.0330, 72.5500, 23.0250, 72.5550), 22, 1.0),
    (925, "Gurukul Rd EB — Gurukul to Memnagar",           "North",   (23.0480, 72.5250, 23.0500, 72.5350), 26, 1.0),
    (926, "Gurukul Rd WB — Memnagar to Gurukul",           "North",   (23.0500, 72.5350, 23.0480, 72.5250), 26, 1.0),
    (927, "Sabarmati Riverfront NB — Extension North",     "North",   (23.0350, 72.5650, 23.0550, 72.5680), 40, 2.2),
    (928, "Sabarmati Riverfront SB — Extension South",     "North",   (23.0550, 72.5680, 23.0350, 72.5650), 40, 2.2),
    (929, "Helmet Cross Rd NB — Helmet to SP Ring",        "West",    (23.0100, 72.5300, 22.9950, 72.5200), 30, 1.5),
    (930, "Helmet Cross Rd SB — SP Ring to Helmet",        "West",    (22.9950, 72.5200, 23.0100, 72.5300), 30, 1.5),
    (931, "Thaltej-Tekra Rd EB — Tekra to Thaltej",       "North",   (23.0450, 72.5100, 23.0470, 72.4990), 25, 1.2),
    (932, "Thaltej-Tekra Rd WB — Thaltej to Tekra",       "North",   (23.0470, 72.4990, 23.0450, 72.5100), 25, 1.2),
    (933, "Naranpura Rd NB — Naranpura to Ankur",          "North",   (23.0550, 72.5500, 23.0650, 72.5480), 24, 1.2),
    (934, "Naranpura Rd SB — Ankur to Naranpura",          "North",   (23.0650, 72.5480, 23.0550, 72.5500), 24, 1.2),
    (935, "Ashram Rd NB — Nehru Br to Usmanpura",          "West",    (23.0350, 72.5600, 23.0450, 72.5650), 30, 1.2),
    (936, "Ashram Rd SB — Usmanpura to Nehru Br",          "West",    (23.0450, 72.5650, 23.0350, 72.5600), 30, 1.2),
    (937, "Satellite Rd NB — Satellite to Ramdev Nagar",   "West",    (23.0150, 72.5050, 23.0250, 72.5080), 28, 1.2),
    (938, "Satellite Rd SB — Ramdev Nagar to Satellite",   "West",    (23.0250, 72.5080, 23.0150, 72.5050), 28, 1.2),
    (939, "Shahibaug Rd NB — Shahibaug to Civil Hospital", "Central", (23.0400, 72.5850, 23.0500, 72.5900), 20, 1.3),
    (940, "Shahibaug Rd SB — Civil Hospital to Shahibaug", "Central", (23.0500, 72.5900, 23.0400, 72.5850), 20, 1.3),
    (941, "Hatkeshwar Rd NB — Hatkeshwar to Amraiwadi",    "East",    (23.0050, 72.6150, 23.0150, 72.6200), 22, 1.2),
    (942, "Hatkeshwar Rd SB — Amraiwadi to Hatkeshwar",    "East",    (23.0150, 72.6200, 23.0050, 72.6150), 22, 1.2),
    (943, "Bapunagar Rd NB — Bapunagar to Nikol",          "East",    (23.0380, 72.6280, 23.0500, 72.6400), 24, 1.8),
    (944, "Bapunagar Rd SB — Nikol to Bapunagar",          "East",    (23.0500, 72.6400, 23.0380, 72.6280), 24, 1.8),
    (945, "Meghaninagar Rd NB — Meghaninagar to Saijpur",  "East",    (23.0450, 72.6200, 23.0550, 72.6300), 20, 1.4),
    (946, "Meghaninagar Rd SB — Saijpur to Meghaninagar",  "East",    (23.0550, 72.6300, 23.0450, 72.6200), 20, 1.4),
    (947, "Maninagar Station Rd NB — Station to Khokhra",  "South",   (22.9950, 72.6000, 23.0050, 72.6050), 20, 1.0),
    (948, "Maninagar Station Rd SB — Khokhra to Station",  "South",   (23.0050, 72.6050, 22.9950, 72.6000), 20, 1.0),
    (949, "Rakhial Rd EB — Rakhial Cross to CTM",          "East",    (23.0150, 72.6100, 23.0200, 72.6200), 22, 1.1),
    (950, "Rakhial Rd WB — CTM to Rakhial Cross",          "East",    (23.0200, 72.6200, 23.0150, 72.6100), 22, 1.1),
    (951, "SP Ring Rd NB — SG Hwy to Gota",               "North",   (23.0800, 72.5100, 23.1000, 72.5100), 55, 2.5),
    (952, "SP Ring Rd SB — Gota to SG Hwy",               "North",   (23.1000, 72.5100, 23.0800, 72.5100), 55, 2.5),
    (953, "132 Ft Ring Rd NB — Shyamal to IIM",           "West",    (23.0150, 72.5250, 23.0290, 72.5250), 40, 1.6),
    (954, "132 Ft Ring Rd SB — IIM to Shyamal",           "West",    (23.0290, 72.5250, 23.0150, 72.5250), 40, 1.6),
    (955, "Zundal-Koba Rd NB — Zundal to Koba",           "North",   (23.1000, 72.6100, 23.1100, 72.5800), 40, 3.5),
    (956, "Zundal-Koba Rd SB — Koba to Zundal",           "North",   (23.1100, 72.5800, 23.1000, 72.6100), 40, 3.5),
    (957, "Sanand Rd EB — Sanand to Sarkhej",              "South",   (22.9900, 72.3800, 22.9900, 72.5100), 48, 7.0),
    (958, "Sanand Rd WB — Sarkhej to Sanand",              "South",   (22.9900, 72.5100, 22.9900, 72.3800), 48, 7.0),
    (959, "Sola Overbridge NB — Sola SG Hwy to Sola Rd",  "North",   (23.0700, 72.5100, 23.0720, 72.5150), 42, 0.5),
    (960, "Sola Overbridge SB — Sola Rd to Sola SG Hwy",  "North",   (23.0720, 72.5150, 23.0700, 72.5100), 42, 0.5),
]

assert len(LINKS) == 200, f"Expected 200 links, got {len(LINKS)}"


def _encode_polyline_simple(lat1, lng1, lat2, lng2):
    """Return a deterministic but plausible-looking encoded polyline string."""
    # Simple placeholder — the real app may or may not use this field.
    def _enc(val):
        val = int(round(val * 1e5))
        val = val << 1
        if val < 0:
            val = ~val
        chunks = []
        while val >= 0x20:
            chunks.append(chr((0x20 | (val & 0x1F)) + 63))
            val >>= 5
        chunks.append(chr(val + 63))
        return "".join(chunks)

    return _enc(lat1) + _enc(lng1) + _enc(lat2 - lat1) + _enc(lng2 - lng1)


def _speed_at_time(base_speed: float, hour: int, minute: int, dow: int) -> float:
    """Simulate realistic speed variation by time-of-day and day-of-week."""
    # Peak hours: 8-10 AM, 5-8 PM
    t = hour + minute / 60.0
    if dow < 5:  # weekday
        if 8 <= t < 10:
            factor = random.uniform(0.40, 0.65)
        elif 17 <= t < 20:
            factor = random.uniform(0.35, 0.60)
        elif 10 <= t < 12:
            factor = random.uniform(0.65, 0.80)
        elif 12 <= t < 14:
            factor = random.uniform(0.60, 0.75)
        elif 14 <= t < 17:
            factor = random.uniform(0.65, 0.82)
        elif 6 <= t < 8:
            factor = random.uniform(0.70, 0.88)
        elif 20 <= t < 22:
            factor = random.uniform(0.75, 0.90)
        elif 22 <= t or t < 1:
            factor = random.uniform(0.85, 1.00)
        else:  # 1-6 AM
            factor = random.uniform(0.90, 1.05)
    else:  # weekend
        if 10 <= t < 13:
            factor = random.uniform(0.60, 0.80)
        elif 17 <= t < 21:
            factor = random.uniform(0.55, 0.75)
        elif 6 <= t < 10:
            factor = random.uniform(0.80, 0.95)
        else:
            factor = random.uniform(0.85, 1.05)

    speed = base_speed * factor + random.uniform(-2, 2)
    return round(max(0.5, speed), 1)


def _link_points(lat1, lng1, lat2, lng2):
    """Generate 6 intermediate points between start and end."""
    points = []
    for i in range(6):
        r = i / 5.0
        lat = round(lat1 + (lat2 - lat1) * r + random.uniform(-0.001, 0.001), 6)
        lng = round(lng1 + (lng2 - lng1) * r + random.uniform(-0.001, 0.001), 6)
        points.append(f"{lat},{lng}")
    return " ".join(points)


def main():
    random.seed(42)
    out_path = os.path.join(os.path.dirname(__file__), "ahmedabad_traffic_speed.csv")

    # 30 days (Jan 1-30 2026), 5-min intervals → 8640 intervals
    start_dt = datetime(2026, 1, 1, 0, 0, 0)
    interval = timedelta(minutes=5)
    num_intervals = 8640  # 30 days

    total_rows = num_intervals * len(LINKS)
    print(f"Generating {total_rows:,} rows to {out_path}…")

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Id", "Speed", "TravelTime", "Status", "DataAsOf",
            "linkId", "linkName", "EncodedPolyLine", "EncodedPolyLineLvls",
            "Borough", "linkPoints",
        ])

        row_id = 0
        for t_idx in range(num_intervals):
            dt = start_dt + interval * t_idx
            dt_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            hour = dt.hour
            minute = dt.minute
            dow = dt.weekday()

            for (link_id, name, zone, coords, base_speed, seg_km) in LINKS:
                row_id += 1
                speed = _speed_at_time(base_speed, hour, minute, dow)
                travel_time = round(seg_km / speed * 3600, 1) if speed > 0 else 9999.0
                # Status: 0 = normal, 1 = light delay, 2 = heavy delay, 3 = stopped
                if speed < 5:
                    status = 3
                elif speed < base_speed * 0.4:
                    status = 2
                elif speed < base_speed * 0.7:
                    status = 1
                else:
                    status = 0

                lat1, lng1, lat2, lng2 = coords
                poly = _encode_polyline_simple(lat1, lng1, lat2, lng2)
                lp = _link_points(lat1, lng1, lat2, lng2)

                writer.writerow([
                    row_id, speed, travel_time, status, dt_str,
                    link_id, name, poly, "BBBBBB", zone,
                    lp,
                ])

            if t_idx % 1000 == 0:
                print(f"  interval {t_idx}/{num_intervals} ({row_id:,} rows written)")

    print(f"Done – {row_id:,} rows written to {out_path}")


if __name__ == "__main__":
    main()
