import { FeaturePlaceholder } from "../../components/FeaturePlaceholder";
import { RoleGuard } from "../../app/RoleGuard";
export const routes = [{ path: "payments", element: <RoleGuard roles={["admin", "staff"]}><FeaturePlaceholder title="Payments" /></RoleGuard> }];
