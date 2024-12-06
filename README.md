# How it works
1. Chunk code using custom code chunker (stolen from Moatless)
2. Generate dep graph (partly stolen from Bloop)
3. Cluster chunks together using multi-level graph clustering algo (basically identifies local communities that are more related amongst each other than they are with outside nodes)
4. Recursively generate summaries from leaf to root

What the clusters represent are functional groupings of code that inter-depend on each other (ie. Web Content Scraping and Integration Feature).

Generation is relatively cheap, fraction of the cost of the ingesting the whole repo
