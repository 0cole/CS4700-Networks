## Summary

This script crawls the website `fakebook.khoury.northeastern.edu` for five secret flags hidden in the profiles of registered users. Once it finds a flag, it is printed out to STDOUT. After finding all five flags, it stops running. The crawler maintains connection by initially logging in and keeping track of the csrf tokens the server sends it. It recursively iterates through all of the profiles by discovering new ones via the friend lists of already visited profiles.

## Approach



## Testing

The testing for the crawler involves a lot of debug print statements to keep track of the progress. We have a global variable called `DEBUG` which toggles these debug statements.