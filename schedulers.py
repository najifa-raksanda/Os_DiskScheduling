"""Finite-batch HDD simulation; physical endpoint travel counted on reversal."""
POLICIES = ('FCFS', 'SSTF', 'SCAN', 'C-SCAN')

def schedule(requests, head=53, policy='FCFS', maximum=199):
    q = list(requests)
    if not 0 <= head <= maximum or any(not 0 <= x <= maximum for x in q):
        raise ValueError('Head and requests must be within disk bounds')
    if policy not in POLICIES:
        raise ValueError('Unknown policy')
    path = [head]
    if not q:
        return 0, path
    if policy == 'FCFS':
        path += q
    elif policy == 'SSTF':
        while q:
            # Arrival order resolves equal-distance ties.
            i = min(range(len(q)), key=lambda i: abs(q[i] - path[-1]))
            path.append(q.pop(i))
    else:
        low = sorted((x for x in q if x <= head), reverse=True)
        high = sorted(x for x in q if x > head)
        path += low
        if high:
            path.append(0)
            if policy == 'SCAN':
                path += high
            else:
                path.append(maximum)  # wrap movement is NOT free
                path += high[::-1]
    return sum(abs(b-a) for a,b in zip(path, path[1:])), path
