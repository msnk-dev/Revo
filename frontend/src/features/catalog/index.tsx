import { FeaturePlaceholder } from "../../components/FeaturePlaceholder";
import { RoleGuard } from "../../app/RoleGuard";
export const routes = [{ path: "catalog", element: <RoleGuard roles={["admin", "staff"]}><FeaturePlaceholder title="Catalog" /></RoleGuard> }];
