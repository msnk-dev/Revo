import { FeaturePlaceholder } from "../../components/FeaturePlaceholder";
import { RoleGuard } from "../../app/RoleGuard";
export const routes = [{ index: true, element: <RoleGuard roles={["admin", "staff"]}><FeaturePlaceholder title="Dashboard" description="Your subscription and revenue overview." /></RoleGuard> }];
