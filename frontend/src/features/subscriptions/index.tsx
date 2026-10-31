import { FeaturePlaceholder } from "../../components/FeaturePlaceholder";
import { RoleGuard } from "../../app/RoleGuard";
export const routes = [{ path: "subscriptions", element: <RoleGuard roles={["admin", "staff"]}><FeaturePlaceholder title="Subscriptions" /></RoleGuard> }];
