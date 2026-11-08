# Where each declared behaviour comes from

The tool knows no provider names. It takes four declared behaviours as input, and this
page is the only place that says what stands behind each one. Two of the four are
documented quotations from one provider, one is the absence of a mechanism, and one is
a construction of mine with no citation at all.

## `key_in_window` and `key_outside_window`

Both are the same documented mechanism, sampled on either side of its retention window.
Quoted from Stripe's API reference, retrieved 2026-11-08 from
<https://docs.stripe.com/api/idempotent_requests>:

> The API supports idempotency for safely retrying requests without accidentally
> performing the same operation twice. When creating or updating an object, use an
> idempotency key. Then, if a connection error occurs, you can safely repeat the request
> without risk of creating a second object or performing the update twice.

> For API v1, you can remove keys from the system automatically after they're at least
> 24 hours old. We generate a new request if a key is reused after the original is pruned.

> The idempotency layer compares incoming parameters to those of the original request and
> errors if they're not the same to prevent a second operation from being performed.

Three things follow, and the matrix uses all three.

1. **Inside the window a replay returns the first result.** That is `key_in_window`.
2. **After the key is pruned the same key is a new request.** That is `key_outside_window`,
   and it is why the window is a required part of a declaration: the identical row is a
   safe resend on one side and a possible second effect on the other.
3. **`at least 24 hours` is a floor, not a duration.** The provider may prune later. A model
   that treats 86400 seconds as the exact boundary is therefore conservative in one
   direction only: a replay at 25 hours may still be inside the provider's real window. The
   matrix still answers `needs_human` there, which is the safe direction to be wrong in.

The third quotation is also why a key-deduping provider is not the same case as a
payload-deduping one: the provider compares parameters and **errors** on a mismatch, so a
replay that presents the same key with different parameters is rejected rather than
silently acted on twice.

## `no_dedupe`

A category, not a provider: the behaviour of a provider that offers no caller-supplied key
and no content comparison. There is nothing to cite, because the claim is that a mechanism
is absent. Reading it as "every provider not named above" would be wrong — this row is only
true of a tool whose provider you have checked and found to have no such mechanism.

## `payload_keyed`

**This one is a construction of mine and has no citation.** It stands for a provider that
compares the request body rather than a key the caller supplies, so a replay is deduplicated
only if the bytes are identical. I did not find a documented provider that behaves exactly
this way, and the matrix would be wrong if such a provider instead compared a subset of
fields or normalised the body first. It is in the matrix because the RFC lists it as one of
the behaviours a tool may declare, not because I verified it.

## What was never done

No provider API was called to produce anything here. No account exists, no key was sent, no
request was made. Every statement above comes from a page anyone can open, and the only
numbers in this repository are counts over the matrix itself, each of which one command
prints.

## Live charge is not a tested path

The `examples/declaration.json` file declares `charge_card` as key-deduping, which is a
plausible declaration for a deployment using the provider quoted above. It is an example of
the file format. Nothing in this repository has ever charged anything.
