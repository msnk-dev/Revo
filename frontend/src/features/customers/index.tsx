import { FeaturePlaceholder } from "../../components/FeaturePlaceholder";
import { RoleGuard } from "../../app/RoleGuard";
export const routes = [{ path: "customers", element: <RoleGuard roles={["admin", "staff"]}><FeaturePlaceholder title="Customers" /></RoleGuard> }];
