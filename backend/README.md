# KabadiLink minimal backend (AWS SAM + Python)

This starter implements the first end-to-end prototype workflow:

- `POST /pickups` — create and save a pickup in DynamoDB
- `GET /pickups` — list pickups; filter with `?householdId=h1`, `?collectorId=c1`, or `?status=Requested`
- `GET /pickups/{id}` — get one pickup
- `PATCH /pickups/{id}/status` — accept, mark on the way, or cancel
- `PATCH /pickups/{id}/weigh-in` — save actual weights and calculate a basic server-side payout

It provisions one DynamoDB table and one Lambda function behind API Gateway. It intentionally has no authentication, in keeping with the current prototype scope.

## Important prototype limitation

Because authentication is not enabled, `hid`, `actorId`, and `collectorId` values supplied by the browser are not verified identities. Anyone who can reach this API may be able to act as another demo user. Keep this API for a controlled prototype only; do not use it with real addresses, payments, or production users. Add authorization before production.

## Prerequisites

- AWS account and configured AWS CLI credentials
- AWS SAM CLI
- Python 3.12 for local testing/build

## Deploy

From this folder:

```bash
sam build
sam deploy --guided
```

Choose a stack name such as `kabadilink-prototype`, region `ap-south-1` if that is where you want the resources, and allow SAM to create IAM roles. After deployment, copy the `ApiBaseUrl` output. Do not guess the URL; use the actual stack output.

## Example requests

Replace `YOUR_API_URL` with the deployed `ApiBaseUrl` output.

Create a pickup:

```bash
curl -X POST "$YOUR_API_URL/pickups" \
  -H 'content-type: application/json' \
  -d '{"hid":"h1","date":"2026-10-15","slot":"8–10 AM","address":"Sector 62, Noida","note":"Call on arrival","kg":{"plastic":3,"wet":5,"ewaste":1}}'
```

List a household's pickups:

```bash
curl "$YOUR_API_URL/pickups?householdId=h1"
```

Get a pickup:

```bash
curl "$YOUR_API_URL/pickups/KL-REPLACE_WITH_ID"
```

Accept a pickup (use an ID from the demo collector data):

```bash
curl -X PATCH "$YOUR_API_URL/pickups/KL-REPLACE_WITH_ID/status" \
  -H 'content-type: application/json' \
  -d '{"status":"Accepted","actorId":"c1"}'
```

Mark on the way:

```bash
curl -X PATCH "$YOUR_API_URL/pickups/KL-REPLACE_WITH_ID/status" \
  -H 'content-type: application/json' \
  -d '{"status":"On the way","actorId":"c1"}'
```

Record actual weight:

```bash
curl -X PATCH "$YOUR_API_URL/pickups/KL-REPLACE_WITH_ID/weigh-in" \
  -H 'content-type: application/json' \
  -d '{"collectorId":"c1","kg":{"plastic":2.5,"wet":4,"ewaste":1}}'
```

## Rate configuration

The current environment variables are deliberately simple placeholders matching the prototype's basic rates. Update them only after confirming the project's approved payout/points rules. The current weigh-in calculation is a minimal backend calculation, not yet the complete tier/bonus/ledger logic from the mock frontend.

## Next integration step

Once deployed, set the frontend API base URL and replace the localStorage implementations in `src/api.ts` for `createPickup`, pickup reads, `acceptPickup`, `markOnTheWay`, and `recordWeighIn` with `fetch()` calls. Keep other mock features local until they are needed.
