import { FeaturePlaceholder } from "../../components/FeaturePlaceholder";
import { RoleGuard } from "../../app/RoleGuard";
export const routes = [{ path: "assistant", element: <RoleGuard roles={["admin", "staff", "customer"]}><FeaturePlaceholder title="AI Assistant" /></RoleGuard> }];
