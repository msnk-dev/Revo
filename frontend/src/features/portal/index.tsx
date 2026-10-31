import { FeaturePlaceholder } from "../../components/FeaturePlaceholder";
import { RoleGuard } from "../../app/RoleGuard";
export const routes = [{ path: "portal", element: <RoleGuard roles={["customer"]}><FeaturePlaceholder title="My account" /></RoleGuard> }];
