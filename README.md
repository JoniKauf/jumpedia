# Jumpedia
This is the source code of Jumpedia.
It is currently **private**.

This README is extended whenever we can think of new things to add and is most likely
VERY incomplete.

## Domain Specific Knowledge
Like in every codebase, there is knowledge specific to that codebase that must be
learned, called domain knowledge.
Domain knowledge is bad for new members of the team, so we try to keep it as low as
possible by following common conventions.

Here is a list of domain specific infos that might help you!

### Design
Before this 3rd or 4th rework of Jumpedia, I (Joni) didn't know much about existing
structures for codebases and just structured it my way. It ended in chaos and very hard
to extend code.

Now we use DDD (Domain Driven Design) Lite (at least close to it).

#### Domain
The foundation lies in `domain/`. Here lies everything that is used everywhere else in
the codebase. It may therefore not reference anything outside of `domain/`.

#### Repository
`repositories/` is at the lowest level. It only knows about `domain/`. It provides the
service layer methods to interact with the database. It is dumb by design and only 
fetches or edits database data. It performs no business logic.

#### Service
`services/` is above the repository layer. It knows about `domain/` and `repositories/`.
It handles ALL business logic and uses repositories to perform its business logic.
There are "public" services which are visible for interfaces (explained next) and
internal services which are used by other services to unify repeated logic and
operations.

#### Interface
`interaces/` is above the service layer. It knows about `domain/` and `services/`. 
It does not directly interact with `repositories/` because that's what the services
are for and handle.

It instead manages how data is displayed to users. This includes managing discord
commands, turning user input into service method input data (via dsls) and then
turning the service output into appropriately displayed data.

...

## TODO

...