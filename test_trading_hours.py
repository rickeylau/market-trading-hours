import json
import unittest
from datetime import date
from trading_hours import ROOT, validate, sessions, render, utc


class TestTradingHours(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads((ROOT/'holidays_snapshot.json').read_text())
        _, years = validate(cls.payload, 2026)
        cls.by_day = {d:(s,e,early) for d,s,e,early in sessions(years)}

    def test_closed_and_weekends(self):
        for d in (date(2026,11,26), date(2026,11,28), date(2026,12,25), date(2027,12,24)):
            self.assertNotIn(d, self.by_day)

    def test_early_close(self):
        for d in (date(2026,11,27), date(2026,12,24), date(2027,11,26)):
            s,e,early = self.by_day[d]
            self.assertTrue(early)
            self.assertEqual((s.strftime('%H:%M'),e.strftime('%H:%M')), ('09:30','13:00'))

    def test_dst(self):
        self.assertEqual(utc(self.by_day[date(2026,3,6)][0]),'20260306T143000Z')
        self.assertEqual(utc(self.by_day[date(2026,3,9)][0]),'20260309T133000Z')
        self.assertEqual(utc(self.by_day[date(2026,11,2)][0]),'20261102T143000Z')

    def test_render(self):
        raw,count,years = render(self.payload,2026)
        self.assertEqual(count,len(self.by_day))
        self.assertEqual(raw.count(b'BEGIN:VEVENT'),count)
        self.assertEqual(raw.count(b'END:VEVENT'),count)
        self.assertTrue(all(len(line)<=75 for line in raw.split(b'\r\n')))
        self.assertEqual(len({x for x in raw.split(b'\r\n') if x.startswith(b'UID:')}),count)
        self.assertEqual(render(self.payload,2026)[0],raw)

    def test_missing_year(self):
        with self.assertRaises(ValueError):
            validate(self.payload,2099)

if __name__ == '__main__':
    unittest.main()
