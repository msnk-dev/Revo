import { AssistantPage } from "./AssistantPanel";
import { RoleGuard } from "../../app/RoleGuard";
export const routes = [{ path: "assistant", element: <RoleGuard roles={["admin", "staff", "customer"]}><AssistantPage /></RoleGuard> }];
