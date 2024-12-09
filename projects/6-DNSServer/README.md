## Summary

According to the project description we broke this project into three phases

### Phase 1 - Local Authoritative Services
We designed a DNS server capable of serving queries for A, CNAME, NS, MX, TXT records for example.com, our local service. If a record did not exist, we responded with an NXDOMAIN message. With the completion of this phase,tests 1-4 successfully passed.

### Phase 2 - Basic Recursion
We implemented the ability to recursively query external services, starting out with the root server. Next, we designed the ability to recursively query external servers to find the final answer based on the chain of responses. To do this, we needed to add support for AA, RD, and RA flags in the response header. Tests 10-16 passed in this phase excluding 14 which we implement next.

### Phase 3 - Advanced features
The final phase consisted of implementing three advanced features, multithreading, bailiwick checking, and caching. 

With the implementation of multithreading, we can speedup the test time by allowing multiple queries to be answered at the same time. This is possible with python's `threading` library, and after the completion of this, test 14 now passes. 

The implementation of bailiwick checking allows use to ignore responses that are not in the same bailiwick as the server providing the request. 
The helper function, `filter_bailiwick()`, is introduced to remove any authority/additional records that are outside the server’s bailiwick. Bailiwick filtering is called immediately after receiving a response from an upstream server in `recursive_resolve()`  before any further processing, allowing our DNS server to pass test 17.

Caching was the final advanced feature we added, allowing for faster response time for addresses that are queried frequently. We have an additional dictionary that keeps track of the record and its ttl. We allocate a thread at the start to persistently manage the cache, deleting expired records if they outlive their ttl. The implementation of caching allows us to pass test 18. 

## Design
With the implementation of caching, test 10 seems to break. It is the only test that does not pass in our submission.