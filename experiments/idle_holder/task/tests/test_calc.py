import unittest
from calc import roman, rle, matrix, dates, intervals


class Roman(unittest.TestCase):
    def test_roundtrip(self):
        for n in (1, 4, 9, 14, 40, 90, 400, 1994, 2024, 3999):
            self.assertEqual(roman.from_roman(roman.to_roman(n)), n)
    def test_values(self):
        self.assertEqual(roman.to_roman(1994), "MCMXCIV")
        self.assertEqual(roman.to_roman(3888), "MMMDCCCLXXXVIII")
    def test_invalid(self):
        for bad in ("IIII", "VX", "", "MMMM", "abc"):
            with self.assertRaises(ValueError): roman.from_roman(bad)
        for bad in (0, 4000, -1):
            with self.assertRaises(ValueError): roman.to_roman(bad)


class RLE(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(rle.encode("aaabcc"), "3a1b2c"); self.assertEqual(rle.encode(""), "")
        self.assertEqual(rle.decode("12a1b"), "a" * 12 + "b")
    def test_roundtrip(self):
        for s in ("", "a", "ab", "aaaaaaaaaaaab", "zzzzzzzzzzzzzzzzzzzzzz"):
            self.assertEqual(rle.decode(rle.encode(s)), s)
    def test_invalid(self):
        with self.assertRaises(ValueError): rle.encode("a1")
        for bad in ("a", "3", "0a", "3a4"):
            with self.assertRaises(ValueError): rle.decode(bad)


class Matrix(unittest.TestCase):
    def test_transpose(self):
        self.assertEqual(matrix.transpose([[1, 2, 3], [4, 5, 6]]), [[1, 4], [2, 5], [3, 6]])
        self.assertEqual(matrix.transpose([]), [])
        with self.assertRaises(ValueError): matrix.transpose([[1, 2], [3]])
    def test_multiply(self):
        self.assertEqual(matrix.multiply([[1, 2], [3, 4]], [[5, 6], [7, 8]]), [[19, 22], [43, 50]])
        self.assertEqual(matrix.multiply([[1, 2, 3]], [[1], [2], [3]]), [[14]])
        with self.assertRaises(ValueError): matrix.multiply([[1, 2]], [[1, 2]])


class Dates(unittest.TestCase):
    def test_days(self):
        self.assertEqual(dates.days_between("2024-01-01", "2024-03-01"), 60)
        self.assertEqual(dates.days_between("2023-01-01", "2023-03-01"), 59)
        self.assertEqual(dates.days_between("2024-03-01", "2024-01-01"), -60)
        self.assertEqual(dates.days_between("1900-02-28", "1900-03-01"), 1)
        self.assertEqual(dates.days_between("2000-02-28", "2000-03-01"), 2)
    def test_weekday(self):
        self.assertEqual(dates.weekday("2026-09-13"), "Sunday")
        self.assertEqual(dates.weekday("2000-01-01"), "Saturday")
        self.assertEqual(dates.weekday("1969-07-20"), "Sunday")


class Intervals(unittest.TestCase):
    def test_merge(self):
        self.assertEqual(intervals.merge([(8, 10), (1, 3), (2, 6), (10, 11)]), [(1, 6), (8, 11)])
        self.assertEqual(intervals.merge([]), [])
    def test_gaps(self):
        self.assertEqual(intervals.gaps([(1, 3), (6, 8)], 0, 10), [(0, 1), (3, 6), (8, 10)])
        self.assertEqual(intervals.gaps([(0, 10)], 0, 10), [])
        self.assertEqual(intervals.gaps([], 2, 5), [(2, 5)])


if __name__ == "__main__":
    unittest.main()
