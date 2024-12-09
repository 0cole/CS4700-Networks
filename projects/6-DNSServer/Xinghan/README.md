## Summary

According to the project description we set this project into three phase
phase 1 include inplement of Local Authoritative Service
such as 
Parse zone file.
Serve A, CNAME, NS, MX, TXT requests for example.com..
Return NXDOMAIN if record not found.
By finihs this phase we are able to pass test 1-4

for next phase we need to implement basic recursion and this include
Implement queries to root server and following chain until you get the final answer.
Handle AA, RD, RA flags correctly.
Handle just one client query at a time initially.
by finishing this phase we are ablt to pass test 10 to 16 except 14

final phase is the implement of following three function
support for run multiple client requests in parallel, this will allow us to pass test 14

Integrate bailiwick checks could help me pass test 17

Implement caching and TTL respect can pass the final test 18.

To make multiple client requests to be processed in parallel
We used threading

For queries that require recursion, we made the code spawns a new thread to handle the recursion.

The main event loop continues to process new requests while recursion is performed in the background.

This step was implemented very smoothly, and test14 passed.

The next step is to implement bailiwick checking

We do this by filters out authority and additional records that are not within the bailiwick of the server currently providing the delegation.

A helper function filter_bailiwick() is introduced to remove any records (from authority and additional sections) that are outside the server’s bailiwick.

Bailiwick filtering is applied immediately after receiving a response from an upstream server in recursive_resolve() and before any further processing.