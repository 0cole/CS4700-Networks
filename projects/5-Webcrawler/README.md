## Summary

This script crawls the website `fakebook.khoury.northeastern.edu` for five secret flags hidden in the profiles of registered users. Once it finds a flag, it is printed out to STDOUT. After finding all five flags, it stops running. The crawler maintains connection by initially logging in and keeping track of the csrf tokens the server sends it. It recursively iterates through all of the profiles by discovering new ones via the friend lists of already visited profiles.

## Testing/Approach

The testing for the crawler involves a lot of debug print statements to keep track of the progress. We have a global variable called `DEBUG` which toggles these debug statements. The main idea is printing all the message the crawle send and what the server reply. Some of the challenge we faced is mainly solved by this way of debugging. For example, when we successfully get the csrftoken and the csrfmiddlewaretoken. We were still not able to login into the server. After observe the printed message from the sever. We find the problem is mainly about we fogot to handle 302 - Found error. After just the code to request again using the new url when receving 302 error. We have successfully logined into the website.
