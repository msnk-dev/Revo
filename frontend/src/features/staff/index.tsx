import { FeaturePlaceholder } from "../../components/FeaturePlaceholder";
import { RoleGuard } from "../../app/RoleGuard";
export const routes = [{ path: "staff", element: <RoleGuard roles={["admin"]}><FeaturePlaceholder title="Staff" /></RoleGuard> }];
