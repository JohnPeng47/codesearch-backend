def measure_closeness_bytes(cluster, input_chunks, window = 1000):
    """
    Measures the extent to which clusters are constructed from contiguous chunks 
    in the input sequence, using a contiguous sliding window
    """
    score = 0
    total_score = len(cluster.chunks)
    prev_chunk = cluster.chunks[0]
    
    for c in cluster.chunks[1:]:
        curr_index = input_chunks.index(c)
        prev_index = input_chunks.index(prev_chunk)
        # actually good case, out of order
        if curr_index < prev_index:
            continue
        
        # print("Curr chunk: ", input_chunks[curr_index].id)
        # print("Diff chunks: ", [(chunk.id, len(chunk.get_content())) for chunk in input_chunks[prev_index:curr_index]] )        
        # TODO: calculate the token length?
        byte_diff = sum([len(chunk.get_content()) for
                           chunk in input_chunks[prev_index:curr_index]])
        
        if byte_diff <= window:
            score += 1
        prev_chunk = c

    return score / total_score

def measure_closeness_chunks(cluster, input_chunks, window = 3):
    """
    Measures the extent to which clusters are constructed from contiguous chunks 
    in the input sequence, using a contiguous sliding window
    """
    score = 0
    total_score = len(cluster.chunks) - 1 if len(cluster.chunks) > 1 else 1
    prev_chunk = cluster.chunks[0]
    
    for c in cluster.chunks[1:]:
        curr_index = input_chunks.index(c)
        prev_index = input_chunks.index(prev_chunk)
        # actually good case, out of order
        if curr_index < prev_index:
            continue

        # print("Curr chunk: ", input_chunks[curr_index].id)
        # print("Prev chunk: ", input_chunks[prev_index].id)
        if curr_index - prev_index <= window:
            score += 1
        
        prev_chunk = c

    return score / total_score

def measure_bytes_agg(cluster, input_chunks):
    """
    Measures the extent to which clusters are constructed from contiguous chunks 
    in the input sequence, using a contiguous sliding window
    """
    scores = []
    prev_chunk = cluster.chunks[0]
    
    for c in cluster.chunks[1:]:
        curr_index = input_chunks.index(c)
        prev_index = input_chunks.index(prev_chunk)

        start_idx = min(curr_index, prev_index)
        end_idx = max(curr_index, prev_index)
        between = input_chunks[start_idx:end_idx]

        byte_count = sum([len(chunk.get_content()) for chunk in between])
        scores.append(byte_count)

        prev_chunk = c
    return scores
