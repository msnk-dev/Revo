import { FeaturePlaceholder } from "../../components/FeaturePlaceholder";
import { RoleGuard } from "../../app/RoleGuard";
export const routes = [{ path: "invoices", element: <RoleGuard roles={["admin", "staff"]}><FeaturePlaceholder title="Invoices" /></RoleGuard> }];
