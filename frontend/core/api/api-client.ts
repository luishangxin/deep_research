import { Client } from "@langchain/langgraph-sdk";
import { getLangGraphBaseURL } from "@/core/config";

let _singleton: Client | null = null;

export function getAPIClient(): Client {
    if (!_singleton) {
        _singleton = new Client({
            apiUrl: getLangGraphBaseURL(),
        });
    }
    return _singleton;
}
