# AI News Agent: Clarification, Web Search, Progress, and Choice UI

## 1. System instruction block

```text
You are a moderator-controlled Indonesian news-writing agent.

DECISION PRIORITY
1. If the request is clear and supported by approved evidence, complete it without
   asking a question.
2. If ambiguity is low-stakes, choose a reasonable default, state the assumption
   in one sentence, and proceed.
3. Ask only when ambiguity materially changes factual accuracy, tone, or format,
   or when a named subject may be unverified, nonexistent, or mistyped.
4. Ask at most one question per turn. Use ask_user_choice with 2-4 concrete,
   mutually exclusive options. Never ask “what do you mean?” or ask what happened
   before establishing that a real event exists.
5. If a product, company, person, or event is unsupported, state that no approved
   source confirms it. Do not claim nonexistence without verification. Offer
   choices such as rumor/speculation, clearly fictional concept, satire/parody,
   or correcting the name.

WEB SEARCH
- Search for real people, events, companies, products, factual claims, and terms
  such as latest, current, recent, today, or breaking.
- Do not search for requests explicitly marked fictional, hypothetical, satire,
  parody, or creative concept unless the user asks for real-world comparison.
- Search results are recommendations until the moderator approves them.
- Attribute web-grounded claims and include the exact source URL.
- Keep quotations brief. Paraphrase the rest; never reproduce large source blocks.

SAFETY AND GROUNDING
- Never invent names, dates, numbers, quotations, events, or sources.
- Keep document evidence, web evidence, and user-provided facts distinguishable.
- Never publish automatically. Return a draft for moderator review.
```

## 2. Tool definitions

The live JSON schemas are also available from `GET /tools/definitions`.

### `web_search`

```json
{
  "type": "function",
  "function": {
    "name": "web_search",
    "description": "Search the current web for factual claims about real people, events, companies, products, or recent news. Do not call for explicitly fictional or hypothetical requests.",
    "parameters": {
      "type": "object",
      "required": ["query"],
      "properties": {
        "query": { "type": "string", "maxLength": 600 },
        "count": { "type": "integer", "minimum": 1, "maximum": 10, "default": 5 },
        "freshness": { "type": ["string", "null"], "enum": ["pd", "pw", "pm", "py", null] },
        "country": { "type": "string", "default": "MY" },
        "search_language": { "type": "string", "default": "id" }
      }
    }
  }
}
```

### `ask_user_choice`

```json
{
  "type": "function",
  "function": {
    "name": "ask_user_choice",
    "description": "Ask one material clarification as tappable choices.",
    "parameters": {
      "type": "object",
      "required": ["lead_in", "question", "options", "select_type", "field"],
      "properties": {
        "lead_in": { "type": "string", "maxLength": 300 },
        "question": { "type": "string", "maxLength": 300 },
        "options": {
          "type": "array",
          "minItems": 2,
          "maxItems": 4,
          "items": { "type": "string" }
        },
        "select_type": { "type": "string", "enum": ["single", "multi"] },
        "field": { "type": "string", "maxLength": 100 }
      }
    }
  }
}
```

Example invocation:

```json
{
  "name": "ask_user_choice",
  "arguments": {
    "lead_in": "Tidak ada sumber yang disetujui yang mengonfirmasi ‘iPhone Duo’, jadi jenis kontennya belum jelas.",
    "question": "Bagaimana topik ini harus diperlakukan?",
    "options": [
      "Spekulasi atau rumor",
      "Konsep fiksi",
      "Satire atau parodi",
      "Nama yang dimaksud berbeda"
    ],
    "select_type": "single",
    "field": "subject_intent"
  }
}
```

## 3. Progress and streaming

Status messages:

1. `checking_request` — “Memeriksa fakta dan ambiguitas penting…”
2. `searching_sources` — “Mencari sumber web terbaru dan relevan…”
3. `drafting_article` — “Menyusun draf berita dari sumber yang disetujui…”
4. `finalizing` — “Memeriksa atribusi, sitasi, dan format artikel…”
5. `complete` — replace progress with the structured article or choice tool.

`POST /news/generate-stream` returns newline-delimited JSON. Minimal consumer:

```ts
const response = await fetch('/news/generate-stream', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(payload),
});

const reader = response.body!.getReader();
const decoder = new TextDecoder();
let buffer = '';

while (true) {
  const { value, done } = await reader.read();
  if (done) break;
  buffer += decoder.decode(value, { stream: true });
  const lines = buffer.split('\n');
  buffer = lines.pop() ?? '';
  for (const line of lines) {
    if (!line) continue;
    const event = JSON.parse(line);
    if (event.type === 'status') setStatus(event.message);
    if (event.type === 'complete') handleAgentResponse(event.data);
    if (event.type === 'error') setError(event.message);
  }
}
```

Ollama token streaming can be added later by emitting `partial` events from its
streaming chat iterator. Accumulate all content and tool calls before appending
the assistant message back into the tool loop.

## 4. React choice rendering

The production implementation is `resources/js/pages/admin/intelligentnewscreator/chat.tsx`.
The minimal response handler is:

```tsx
type ChoiceCall = {
  name: 'ask_user_choice';
  arguments: {
    lead_in: string;
    question: string;
    options: string[];
    select_type: 'single' | 'multi';
    field: string;
  };
};

function AgentMessage({ response }: { response: { tool_call?: ChoiceCall } }) {
  const call = response.tool_call;
  if (call?.name !== 'ask_user_choice') return <Article data={response} />;

  return (
    <Card>
      <CardHeader>
        <p>{call.arguments.lead_in}</p>
        <CardTitle>{call.arguments.question}</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-2">
        {call.arguments.options.map(option => (
          <Button
            key={option}
            variant="outline"
            onClick={() => sendUserTurn({
              field: call.arguments.field,
              value: option,
            })}
          >
            {option}
          </Button>
        ))}
      </CardContent>
    </Card>
  );
}
```

Edge cases:

- Free-text replies remain valid; send them as the answer for the active field.
- A single-select click submits immediately. Multi-select requires confirmation.
- Disable confirmation when nothing is selected.
- Prevent double submission while a request is active.
- Never re-ask a field already stored in `user_facts`.
- If the user answers another issue, save it and re-evaluate rather than repeating
  the same card blindly.
- Expire or refresh old web recommendations before using them for current news.
- If search is unavailable, disclose that verification could not be completed and
  do not invent an answer.

## Configuration

```env
BRAVE_SEARCH_API_KEY=your_key
WEB_SEARCH_TIMEOUT_SECONDS=15
```

Without a Brave key, the service remains fully local and falls back to approved
documents plus structured clarification.
