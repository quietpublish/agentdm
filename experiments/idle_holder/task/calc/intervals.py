def merge(intervals):
    """Merge overlapping/touching closed intervals [(1,3),(2,6),(8,10),(10,11)] -> [(1,6),(8,11)]. Input unordered."""
    raise NotImplementedError


def gaps(intervals, lo, hi):
    """Closed intervals inside [lo, hi] not covered by merge(intervals). e.g. gaps([(1,3),(6,8)],0,10)->[(0,1),(3,6),(8,10)]"""
    raise NotImplementedError
