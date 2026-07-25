# FIXME

## Bugs

- the youtube download gives this error. (truncated for brevity):
> ERROR: [youtube] wwHrEhOLIJ0: Please sign in. Use --cookies-from-browser or --cookies...

## Unimplemented features

- Verify whether remove + reorder are implemented. If not, please add.

## Bad UX

- Join by clicking on session on homepage is weird. The homepage should not list existing sessions. Instead, it should show a count of how many sessions exist and include some text that the user should ask for the 6-digit session id to join with.
- Sessions shouldn't have an extra 6-digit password field to join. Instead, just knowing the 6-digit session id should be all the user needs to join.
- The host of the session is shown twice. Just let the user-presence badges list members

## Tech stuff

- Backend server should log more progress through the track processing pipeline
- How does state "clean up" for sessions? Do we have anything that cleans up all track data when a session is "over"?
