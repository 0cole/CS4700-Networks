## Summary

This script emulates the behavior of a BGP router. It is able to communicate with external networks and manage a forwarding table that is capable of coalescing and disaggregating upon receiving updates and withdrawals.

My implementation of this router passes every test provided in `configs`.

## Approach

I developed my router by following the progression of the tests provided to me. 

I started out with handling `update`, `data`, and `dump` messages. I populated a forwarding table with every network that sent an `update` message. With this forwarding table, I was able to redirect the `data` messages and dump my entire fowarding table when I received `dump` messages.

Next, I implemented a optimal peer algorithm which determined the best peer to use when forwarding a `data` message. This algorithm filtered all the routes by comparing several criteria. I was also able to complete the longest prefix matching here as well.

`withdraw` was the next thing that I implemented. This removed networks from my forwarding table.

I then spent some time trying to implement coalesce. It took a few hours, but I was able to successfully implement it.

Finally, I implemented a disaggregation algorithm which used my earlier implementation of coalesce to rebuild the new forwarding table.

# Testing

All of the testing for this program was done using this the tests in `configs`. I started off reading the first two milestone tests to build an understanding, and then used the remaining tests as a benchmark for my progress.
