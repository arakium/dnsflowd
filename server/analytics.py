import database
def get_top(limit = 10):
    data = database.get_recent_queries()
    src_idx = 3
    frequency_map = {}
    for query in data:
        if query[src_idx] in frequency_map:
            frequency_map[query[src_idx]] += 1
        else:
            frequency_map[query[src_idx]] = 1
    frequency_list = list(frequency_map.items())
    print(frequency_list)
    frequency_list.sort(key=lambda item: item[1], reverse=True)
    return frequency_list[:limit]