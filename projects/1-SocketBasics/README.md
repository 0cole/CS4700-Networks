## Approach

This script supports both non-TLS and TLS encryption socket communication. This can be specified by adding the `-s` argument when invoking the script. To change which port this script connects to, add `-p <Port>` as an argument during invocation.

For the guessing algorith, I had originally tried to heavily optimize due to the large size of the wordlist. However, after learning that a ceiling of 500 guesses was permitted, I decided to take a more relaxed approach which made the logic far simpler. My algorithm can consistently guess the word in 8-11 guesses and works by filtering the remaining wordlist based off of the most recent guess feedback. The filter eliminates any words that contain letters that were returned with a 0 mark from the previous guess. It also filters out words that do not have letters that returned a 1 or 2 mark from the previous guess. Once the previous wordlist has been completely filtered and only valid words remain in the new one, the old wordlist object is set to the newly filtered wordlist, and the algorithm iterates with the same wordlist object as used previously. This process continues until the word has been correctly guessed. After a successful guess, the flag is printed, the connection to the server socket is terminated, and the script finishes running.

## Testing

This code successfully retrieves the secret flags with both non-tls-encrypted and tls-encrypted communication. I tested my code at checkpoints throughout development to ensure no mistakes were being made to avoid any confusion when it came time to push to gradescope.

## Notes

link to hw for my reference - https://4700.network/docs/projects/socketbasics/
