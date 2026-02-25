notes from meeting:
- maybe use 'click' for the cli?
- no, 'argparse' is better for zero-dependency.
- the 'truth map' is the most important part.
- if a directory has a .git folder, we MUST use git ls-files.
- if no .git, just walk.
- make it fast.
- i want to see a progress bar if possible.
